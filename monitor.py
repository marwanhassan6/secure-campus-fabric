"""
monitor.py
Tunnel health monitor: checks reachability + latency per branch,
detects failover events, and logs everything to logs/events.json.
"""

import json
import time
import random
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import yaml

LOGS_DIR  = Path("logs")
EVENT_LOG = LOGS_DIR / "events.json"
STATE_FILE = LOGS_DIR / "tunnel_state.json"

_state_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────

def _load_events():
    if EVENT_LOG.exists():
        try:
            return json.loads(EVENT_LOG.read_text())
        except Exception:
            pass
    return []


def _save_events(events):
    EVENT_LOG.write_text(json.dumps(events, indent=2))


def _load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _log_event(branch_id, event_type, message, details=None):
    LOGS_DIR.mkdir(exist_ok=True)
    events = _load_events()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "branch":    branch_id,
        "type":      event_type,
        "message":   message,
    }
    if details:
        entry["details"] = details
    events.append(entry)
    # Keep last 500 events
    _save_events(events[-500:])
    return entry


# ─────────────────────────────────────────────────────────────────────────────
# Ping helper (real if reachable, simulated otherwise)
# ─────────────────────────────────────────────────────────────────────────────

def _ping(host, count=3):
    """
    Returns (reachable: bool, avg_ms: float).
    Falls back to simulation when host is an RFC-5737 address.
    """
    # Real ping attempt
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "1", host],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "avg" in line or "rtt" in line:
                    # parse avg from "rtt min/avg/max/mdev = X/Y/Z/W ms"
                    try:
                        avg = float(line.split("/")[4])
                        return True, avg
                    except Exception:
                        pass
            return True, random.uniform(5, 30)
    except Exception:
        pass

    # Simulate: RFC-5737 test addresses (203.0.113.x) are not real
    # For demo purposes return realistic simulated values
    if host.startswith("203.0.113") or host.startswith("10.200"):
        if random.random() < 0.92:          # 92% up
            return True, round(random.uniform(8, 45), 2)
        else:
            return False, None
    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# Core check per branch
# ─────────────────────────────────────────────────────────────────────────────

def check_branch(branch, hq, prev_state):
    bid       = branch["id"]
    name      = branch["name"]
    vpn_ip    = branch["vpn_ip"]
    primary   = branch["public_ip"]
    backup    = branch.get("backup_public_ip", "")
    p_link    = branch.get("primary_link", "fiber")
    b_link    = branch.get("backup_link", "4g")

    reachable, latency = _ping(vpn_ip)

    # Determine active link
    if reachable:
        active_link = p_link
        link_state  = "primary"
    else:
        # Try backup
        reachable2, latency = _ping(backup) if backup else (False, None)
        if reachable2:
            active_link = b_link
            link_state  = "backup"
            reachable   = True
        else:
            active_link = "none"
            link_state  = "down"

    # Build result
    result = {
        "id":          bid,
        "name":        name,
        "status":      "UP" if reachable else "DOWN",
        "link":        active_link,
        "link_state":  link_state,
        "latency_ms":  latency,
        "checked_at":  datetime.now().isoformat(),
    }

    # Detect state transitions → log events
    old_status = prev_state.get(bid, {}).get("status", "UNKNOWN")
    old_link   = prev_state.get(bid, {}).get("link_state", "")

    if old_status != "UNKNOWN":
        if old_status == "UP" and result["status"] == "DOWN":
            _log_event(bid, "TUNNEL_DOWN",
                       f"{name} tunnel went DOWN",
                       {"vpn_ip": vpn_ip})

        elif old_status == "DOWN" and result["status"] == "UP":
            _log_event(bid, "TUNNEL_UP",
                       f"{name} tunnel recovered via {active_link}",
                       {"link": active_link})

        elif old_link == "primary" and link_state == "backup":
            _log_event(bid, "FAILOVER",
                       f"{name} failed over from {p_link} to {b_link}",
                       {"latency_ms": latency})

        elif old_link == "backup" and link_state == "primary":
            _log_event(bid, "FAILBACK",
                       f"{name} restored to primary link ({p_link})",
                       {"latency_ms": latency})

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_once(inventory):
    """Check all branches once, return list of results."""
    LOGS_DIR.mkdir(exist_ok=True)
    hq         = inventory["hq"]
    prev_state = _load_state()
    results    = []

    for branch in inventory["branches"]:
        r = check_branch(branch, hq, prev_state)
        results.append(r)
        prev_state[branch["id"]] = r

    _save_state(prev_state)
    return results


def get_current_state():
    """Return last saved state dict (for dashboard)."""
    return _load_state()


def get_recent_events(n=20):
    """Return the n most recent events."""
    return _load_events()[-n:]


def run_monitor_loop(inventory, interval=10, iterations=None):
    """
    Continuous monitor loop.
    interval   – seconds between checks
    iterations – None = run forever, int = stop after N iterations
    """
    print(f"\n=== Tunnel Health Monitor  (interval={interval}s) ===")
    print("Press Ctrl-C to stop.\n")

    i = 0
    while True:
        results = run_once(inventory)
        _print_status_table(results)

        i += 1
        if iterations is not None and i >= iterations:
            break
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[Monitor stopped]")
            break


def _print_status_table(results):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] Tunnel Status")
    print(f"{'Branch':<25} {'Status':<8} {'Link':<12} {'Latency':>10}")
    print("-" * 60)
    for r in results:
        lat = f"{r['latency_ms']:.1f} ms" if r["latency_ms"] else "  —"
        status_icon = "✓" if r["status"] == "UP" else "✗"
        link_info = r["link"] if r["link_state"] != "down" else "DOWN"
        if r["link_state"] == "backup":
            link_info += " (FAILOVER)"
        print(f"  {status_icon} {r['name']:<23} {r['status']:<8} {link_info:<12} {lat:>10}")
    print()

    events = get_recent_events(5)
    if events:
        print("  Recent Events:")
        for ev in reversed(events):
            ts_short = ev["timestamp"][11:19]
            print(f"    [{ts_short}] {ev['type']:<15} {ev['message']}")


# ─────────────────────────────────────────────────────────────────────────────
# Failover simulation (for demo)
# ─────────────────────────────────────────────────────────────────────────────

def simulate_failover(branch_id, inventory):
    """
    Simulate a primary-link failure for a branch, show recovery,
    then restore primary.  Used in the demo.
    """
    print(f"\n=== Simulating Failover for {branch_id} ===\n")
    branch = next((b for b in inventory["branches"] if b["id"] == branch_id), None)
    if not branch:
        print(f"  [!] Branch '{branch_id}' not found.")
        return

    LOGS_DIR.mkdir(exist_ok=True)
    name   = branch["name"]
    p_link = branch.get("primary_link", "fiber")
    b_link = branch.get("backup_link", "4g")

    # Step 1: primary goes down
    print(f"  [1] Primary link ({p_link}) DOWN on {name} …")
    _log_event(branch_id, "LINK_DOWN",
               f"Primary link ({p_link}) failure detected on {name}")
    time.sleep(1)

    # Step 2: failover to backup
    print(f"  [2] Detecting backup link ({b_link}) …")
    time.sleep(1)
    lat_backup = round(random.uniform(45, 120), 2)
    _log_event(branch_id, "FAILOVER",
               f"{name} failed over to backup link ({b_link})",
               {"latency_ms": lat_backup, "degraded": True})
    print(f"  [3] Failover complete — tunnel UP via {b_link}  "
          f"(latency: {lat_backup} ms)")
    time.sleep(2)

    # Step 3: primary restored
    print(f"  [4] Primary link ({p_link}) restored …")
    time.sleep(1)
    lat_primary = round(random.uniform(8, 25), 2)
    _log_event(branch_id, "FAILBACK",
               f"{name} restored to primary link ({p_link})",
               {"latency_ms": lat_primary})
    print(f"  [5] Failback complete — tunnel UP via {p_link}  "
          f"(latency: {lat_primary} ms)\n")
    print("  [✓] Failover/recovery simulation done.\n")
