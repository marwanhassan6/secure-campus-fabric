#!/bin/bash
# Route policy — generated 2026-05-02 16:46
# Apply on HQ router to steer branch traffic correctly

# Branch Cairo
ip route add 192.168.1.0/24 via 10.200.0.2 dev wg0
# Failover via backup link
ip route add 192.168.1.0/24 via 203.0.114.10 metric 200 dev eth1 || true

# Branch Alexandria
ip route add 192.168.2.0/24 via 10.200.0.3 dev wg0
# Failover via backup link
ip route add 192.168.2.0/24 via 203.0.114.20 metric 200 dev eth1 || true

# Branch Luxor
ip route add 192.168.3.0/24 via 10.200.0.4 dev wg0
# Failover via backup link
ip route add 192.168.3.0/24 via 203.0.114.30 metric 200 dev eth1 || true
