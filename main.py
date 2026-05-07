#!/usr/bin/env python3
"""
Secure Campus Fabric — Main CLI
Project 3 entry point. Orchestrates config generation, monitoring,
compliance, verification, and demo sequences.
"""
import argparse
import sys
import yaml
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import config_generator
    import monitor
    import compliance
except ImportError as e:
    print(f"[!] Import error: {e}")
    print("    Ensure config_generator.py, monitor.py, and compliance.py are present.")
    sys.exit(1)


def load_inventory(path="inventory.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def cmd_generate(args):
    config_generator.run_generate(args.inventory)


def cmd_monitor(args):
    inv = load_inventory(args.inventory)
    if args.once:
        results = monitor.run_once(inv)
        monitor._print_status_table(results)
    elif args.demo_failover:
        monitor.simulate_failover(args.demo_failover, inv)
    else:
        monitor.run_monitor_loop(inv, interval=args.interval, iterations=args.iterations)


def cmd_compliance(args):
    inv = load_inventory(args.inventory)
    compliance.run_compliance(inv)


def cmd_verify(args):
    from verify import run_verification
    inv = load_inventory(args.inventory)
    run_verification(inv)


def cmd_capture(args):
    from pcap_demo import main as pcap_main
    pcap_main()


def cmd_demo(args):
    """Run the full demo sequence required by the project PDF."""
    print("=" * 70)
    print("  SECURE CAMPUS FABRIC — PROJECT 3 DEMO")
    print("=" * 70)

    inv = load_inventory(args.inventory)

    # 1. Generate
    print("\n>>> [1/6] Generating WireGuard, firewall, and route configs...")
    config_generator.run_generate(args.inventory)

    # 2. Compliance
    print("\n>>> [2/6] Running compliance audit...")
    compliance.run_compliance(inv)

    # 3. Verify connectivity
    print("\n>>> [3/6] Running branch acceptance tests...")
    from verify import run_verification
    run_verification(inv)

    # 4. Monitor health
    print("\n>>> [4/6] Checking initial tunnel health...")
    results = monitor.run_once(inv)
    monitor._print_status_table(results)

    # 5. Simulate failover
    print("\n>>> [5/6] Simulating branch_cairo primary link failure...")
    monitor.simulate_failover("branch_cairo", inv)

    # 6. Packet evidence
    print("\n>>> [6/6] Generating packet-capture evidence...")
    from pcap_demo import generate_mock_evidence
    evidence = generate_mock_evidence(inv)
    Path("logs").mkdir(exist_ok=True)
    Path("logs/capture_evidence.txt").write_text(evidence)
    print("    Saved to logs/capture_evidence.txt")

    print("\n" + "=" * 70)
    print("  DEMO COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  - Start dashboard : python main.py dashboard")
    print("  - View logs       : cat logs/events.json")
    print("  - Add a branch    : Edit inventory.yaml, then: python main.py generate")


def main():
    parser = argparse.ArgumentParser(
        description="Secure Campus Fabric — Project 3 Controller"
    )
    parser.add_argument(
        "-i", "--inventory", default="inventory.yaml",
        help="Path to site inventory YAML"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("generate", help="Generate configs from inventory")

    p_mon = sub.add_parser("monitor", help="Tunnel health monitor")
    p_mon.add_argument("--interval", type=int, default=10,
                       help="Seconds between checks")
    p_mon.add_argument("--iterations", type=int, default=None,
                       help="Stop after N iterations")
    p_mon.add_argument("--once", action="store_true",
                       help="Single check and exit")
    p_mon.add_argument("--demo-failover", metavar="BRANCH_ID",
                       help="Simulate failover for a branch")

    sub.add_parser("compliance", help="Run compliance audit")
    sub.add_parser("verify", help="Run branch acceptance tests")
    sub.add_parser("capture", help="Generate packet-capture evidence")
    sub.add_parser("demo", help="Run full project demo sequence")

    p_dash = sub.add_parser("dashboard", help="Launch web dashboard")
    p_dash.add_argument("--host", default="0.0.0.0")
    p_dash.add_argument("--port", type=int, default=5000)

    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "compliance":
        cmd_compliance(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "capture":
        cmd_capture(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "dashboard":
        try:
            import dashboard
        except ImportError as e:
            print(f"[!] Cannot import dashboard: {e}")
            print("    Install dependencies: pip install -r requirements.txt")
            sys.exit(1)
        print(f"[*] Starting dashboard on http://{args.host}:{args.port}")
        dashboard.app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
