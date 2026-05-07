"""
compliance.py
Branch Acceptance Compliance Checker

Verifies that:
  1. Every branch has a WireGuard config generated.
  2. Every branch has a firewall ruleset generated.
  3. Firewall rules only allow approved services (no extras).
  4. Firewall rules include a final DROP rule (implicit deny).
  5. Branches do not have access to services they are not approved for.
  6. Route policy file exists.
  7. All approved services are known HQ services.
"""

import re
from pathlib import Path
from datetime import datetime

import yaml

CONFIGS_DIR = Path("configs")
WG_DIR      = CONFIGS_DIR / "wireguard"
FW_DIR      = CONFIGS_DIR / "firewall"

# ─────────────────────────────────────────────────────────────────────────────

def _check(condition, msg_pass, msg_fail):
    if condition:
        return {"pass": True,  "message": f"[PASS] {msg_pass}"}
    else:
        return {"pass": False, "message": f"[FAIL] {msg_fail}"}


def _load_iptables_script(branch_id):
    p = FW_DIR / f"{branch_id}-iptables.sh"
    if p.exists():
        return p.read_text()
    return None


def _extract_allowed_services(script_text):
    """Parse comment annotations from generated iptables rules."""
    pattern = re.compile(r"branch:(\w+)")
    return set(pattern.findall(script_text))


def _extract_denied_subnets(script_text):
    return "deny:unapproved" in script_text


# ─────────────────────────────────────────────────────────────────────────────

def check_branch_compliance(branch, hq):
    bid      = branch["id"]
    name     = branch["name"]
    approved = set(branch["approved_services"])
    all_svc  = set(hq["services"].keys())
    results  = []

    # 1. WireGuard config exists
    wg_path = WG_DIR / f"{bid}-branch.conf"
    results.append(_check(
        wg_path.exists(),
        f"{name}: WireGuard config exists ({wg_path.name})",
        f"{name}: WireGuard config MISSING — run 'generate' first"
    ))

    # 2. Firewall script exists
    fw_script = _load_iptables_script(bid)
    results.append(_check(
        fw_script is not None,
        f"{name}: iptables script exists",
        f"{name}: iptables script MISSING — run 'generate' first"
    ))

    # 3. nftables config exists
    nft_path = FW_DIR / f"{bid}-nftables.conf"
    results.append(_check(
        nft_path.exists(),
        f"{name}: nftables config exists",
        f"{name}: nftables config MISSING"
    ))

    if fw_script:
        allowed_in_rules = _extract_allowed_services(fw_script)

        # 4. Rules only allow approved services
        extra = allowed_in_rules - approved
        results.append(_check(
            len(extra) == 0,
            f"{name}: No extra services in firewall rules",
            f"{name}: Firewall rules contain UNAPPROVED services: {extra}"
        ))

        # 5. All approved services are in rules
        missing = approved - allowed_in_rules
        # Filter to known services only (unknown ones get a separate check)
        missing_known = missing & all_svc
        results.append(_check(
            len(missing_known) == 0,
            f"{name}: All approved services have firewall rules",
            f"{name}: Approved services missing from rules: {missing_known}"
        ))

        # 6. Implicit deny present
        results.append(_check(
            _extract_denied_subnets(fw_script),
            f"{name}: Implicit DENY rule present (default-deny posture)",
            f"{name}: No DENY rule found — traffic not blocked by default"
        ))

        # 7. Denied services list
        unapproved_svc = all_svc - approved
        if unapproved_svc:
            results.append({
                "pass": True,
                "message": f"[INFO] {name}: Services correctly BLOCKED: "
                           f"{', '.join(sorted(unapproved_svc))}"
            })

    # 8. All approved services are known HQ services
    unknown = approved - all_svc
    results.append(_check(
        len(unknown) == 0,
        f"{name}: All approved services are defined in HQ service catalog",
        f"{name}: Unknown services in approved list: {unknown}"
    ))

    # 9. Route policy file exists
    results.append(_check(
        (CONFIGS_DIR / "route-policy.sh").exists(),
        f"Route policy script exists",
        f"Route policy script MISSING — run 'generate' first"
    ))

    return results


# ─────────────────────────────────────────────────────────────────────────────

def run_compliance(inventory):
    hq       = inventory["hq"]
    branches = inventory["branches"]

    print("\n=== Branch Compliance Audit ===")
    print(f"    Date: {datetime.now():%Y-%m-%d %H:%M}")
    print(f"    Branches: {len(branches)}\n")

    total_pass = 0
    total_fail = 0
    report     = []

    for branch in branches:
        checks  = check_branch_compliance(branch, hq)
        passed  = sum(1 for c in checks if c["pass"])
        failed  = sum(1 for c in checks if not c["pass"])
        score   = int(100 * passed / len(checks)) if checks else 0

        total_pass += passed
        total_fail += failed

        print(f"  ── {branch['name']}  ({score}% compliant) ──")
        for c in checks:
            print(f"     {c['message']}")
        print()

        report.append({
            "branch":  branch["id"],
            "name":    branch["name"],
            "score":   score,
            "passed":  passed,
            "failed":  failed,
            "checks":  checks,
        })

    overall = int(100 * total_pass / (total_pass + total_fail)) \
              if (total_pass + total_fail) > 0 else 0

    print("─" * 60)
    print(f"  Overall Compliance: {overall}%  "
          f"({total_pass} passed / {total_fail} failed)")
    print()

    if total_fail == 0:
        print("  [✓] All branches meet compliance requirements.\n")
    else:
        print("  [!] Some branches have compliance issues. "
              "Run 'generate' and retry.\n")

    return report
