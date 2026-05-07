# 1. Install deps (only Flask is extra; PyYAML is usually built-in)
pip install -r requirements.txt

# 2. Run the full demo sequence in one command
python main.py demo

The demo command executes:
Config generation (WireGuard + firewall + routes)
Compliance audit
Branch acceptance tests
Tunnel health check
Failover simulation for branch_cairo
Packet-capture evidence report

# Generate all configs
python main.py generate

# Run compliance audit
python main.py compliance

# Check tunnels once
python main.py monitor --once

# Simulate failover for a branch
python main.py monitor --demo-failover branch_cairo

# Start monitoring loop (Ctrl-C to stop)
python main.py monitor --interval 10

# Launch web dashboard (http://localhost:5000)
python main.py dashboard

# Run branch acceptance tests
python main.py verify

# Generate capture evidence
python main.py capture


configs/wireguard/*.conf — WireGuard peer configs
configs/firewall/*-iptables.sh — iptables rule scripts
configs/firewall/*-nftables.conf — nftables rule sets
configs/route-policy.sh — iproute2 routing policy
logs/events.json — state-transition events (failover, recovery, etc.)
logs/tunnel_state.json — last-known tunnel state
logs/capture_evidence.txt — packet-flow / encapsulation report
