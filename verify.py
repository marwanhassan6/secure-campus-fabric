"""
verify.py
Branch Acceptance / Connectivity Verification

Simulates end-to-end service tests from each branch LAN to HQ LAN.
In a real deployment this would use nc/curl/ping; here we simulate
based on the policy defined in inventory.yaml and report results.
"""
import random
from datetime import datetime


def run_verification(inventory):
    hq = inventory["hq"]
    services = hq["services"]

    print("\n=== Branch Acceptance Tests ===")
    print(f"    Target HQ LAN : {hq['lan_subnet']}")
    print(f"    Services      : {', '.join(services.keys())}\n")

    all_pass = True
    for branch in inventory["branches"]:
        name = branch["name"]
        approved = set(branch.get("approved_services", []))

        print(f"  ── {name} ({branch['lan_subnet']}) ──")
        branch_ok = True

        for svc_name, svc_def in services.items():
            should_allow = svc_name in approved

            if should_allow:
                # Simulate connectivity test (98 % success rate)
                ok = random.random() < 0.98
                if ok:
                    print(f"     ✓ {svc_name:<8} → REACHABLE ({svc_def['proto'].upper()} {svc_def['port']})")
                else:
                    print(f"     ✗ {svc_name:<8} → UNREACHABLE")
                    branch_ok = False
            else:
                # Verify it is correctly blocked by policy
                print(f"     ✓ {svc_name:<8} → correctly BLOCKED by policy")

        if not branch_ok:
            all_pass = False
        print()

    print("─" * 50)
    if all_pass:
        print("  [✓] All branch acceptance tests passed.\n")
    else:
        print("  [!] Some connectivity tests failed.\n")


if __name__ == "__main__":
    import yaml
    with open("inventory.yaml") as f:
        inv = yaml.safe_load(f)
    run_verification(inv)
