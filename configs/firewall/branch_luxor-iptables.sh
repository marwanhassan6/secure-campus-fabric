#!/bin/bash
# iptables rules for Branch Luxor
# Generated 2026-05-02 16:46
# Apply on the branch router (or HQ forward chain)

# Flush existing FORWARD rules for this branch
iptables -F FORWARD

# Allow established/related traffic
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow approved services from branch LAN → HQ LAN
iptables -A FORWARD -s 192.168.3.0/24 -d 192.168.0.0/24 -p tcp --dport 80 -j ACCEPT -m comment --comment 'branch:http'
iptables -A FORWARD -s 192.168.3.0/24 -d 192.168.0.0/24 -p tcp --dport 443 -j ACCEPT -m comment --comment 'branch:https'
iptables -A FORWARD -s 192.168.3.0/24 -d 192.168.0.0/24 -p udp --dport 53 -j ACCEPT -m comment --comment 'branch:dns'
iptables -A FORWARD -s 192.168.3.0/24 -d 192.168.0.0/24 -p udp --dport 123 -j ACCEPT -m comment --comment 'branch:ntp'

# Block all other branch → HQ traffic
iptables -A FORWARD -s 192.168.3.0/24 -d 192.168.0.0/24 -j DROP -m comment --comment 'deny:unapproved'

# NAT: masquerade branch traffic leaving HQ to internet (PAT)
iptables -t nat -A POSTROUTING -s 10.200.0.0/24 -o eth0 -j MASQUERADE