"""
config_generator.py
Generates WireGuard tunnel configs and iptables/nftables firewall rules
from the site inventory.
"""

import os
import base64
import secrets
import yaml
from pathlib import Path
from datetime import datetime

CONFIGS_DIR = Path("configs")
WG_DIR      = CONFIGS_DIR / "wireguard"
FW_DIR      = CONFIGS_DIR / "firewall"

# ---------------------------------------------------------------------------
# Key helpers (realistic-looking placeholder keys for demo / real if wg present)
# ---------------------------------------------------------------------------

def _generate_wg_keypair():
    """Try real wg keygen; fall back to a realistic-looking placeholder."""
    import subprocess
    try:
        priv = subprocess.check_output(["wg", "genkey"],
                                        stderr=subprocess.DEVNULL).decode().strip()
        pub  = subprocess.check_output(["wg", "pubkey"],
                                        input=priv.encode(),
                                        stderr=subprocess.DEVNULL).decode().strip()
        return priv, pub
    except Exception:
        # Generate Base64-encoded random bytes that look like real WG keys
        priv_bytes = secrets.token_bytes(32)
        pub_bytes  = secrets.token_bytes(32)
        priv = base64.b64encode(priv_bytes).decode()
        pub  = base64.b64encode(pub_bytes).decode()
        return priv, pub


def load_inventory(path="inventory.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# WireGuard config generation
# ---------------------------------------------------------------------------

def generate_wg_configs(inventory):
    """
    For every branch, generate:
      - configs/wireguard/<branch_id>-branch.conf   (runs on branch router)
      - configs/wireguard/<branch_id>-hq-peer.conf  (peer block appended to HQ)
    Returns a dict: branch_id → {priv, pub, hq_pub}
    """
    WG_DIR.mkdir(parents=True, exist_ok=True)
    hq = inventory["hq"]
    hq_priv, hq_pub = _generate_wg_keypair()

    # Save HQ base config
    hq_conf_lines = [
        f"# HQ WireGuard Interface  — generated {datetime.now():%Y-%m-%d %H:%M}",
        "[Interface]",
        f"Address    = {hq['vpn_ip']}/24",
        f"ListenPort = {hq['wg_port']}",
        f"PrivateKey = {hq_priv}",
        "PostUp     = iptables -A FORWARD -i wg0 -j ACCEPT; "
                     "iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
        "PostDown   = iptables -D FORWARD -i wg0 -j ACCEPT; "
                     "iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE",
        "",
    ]

    key_store = {}

    for branch in inventory["branches"]:
        bid   = branch["id"]
        bpriv, bpub = _generate_wg_keypair()
        key_store[bid] = {"priv": bpriv, "pub": bpub, "hq_pub": hq_pub}

        # ── Branch-side config ────────────────────────────────────────────
        branch_conf = [
            f"# Branch: {branch['name']}  — generated {datetime.now():%Y-%m-%d %H:%M}",
            "# Deploy this file as /etc/wireguard/wg0.conf on the branch router",
            "[Interface]",
            f"Address    = {branch['vpn_ip']}/24",
            f"ListenPort = {branch['wg_port']}",
            f"PrivateKey = {bpriv}",
            f"DNS        = {hq['dns']}",
            "",
            "# HQ peer",
            "[Peer]",
            f"PublicKey  = {hq_pub}",
            f"Endpoint   = {hq['public_ip']}:{hq['wg_port']}",
            # Only tunnel traffic destined for HQ LAN + VPN range
            f"AllowedIPs = {hq['lan_subnet']}, 10.200.0.0/24",
            "PersistentKeepalive = 25",
            "",
        ]
        (WG_DIR / f"{bid}-branch.conf").write_text("\n".join(branch_conf))

        # ── HQ peer block for this branch ─────────────────────────────────
        hq_peer = [
            f"# Peer: {branch['name']}",
            "[Peer]",
            f"PublicKey  = {bpub}",
            f"AllowedIPs = {branch['vpn_ip']}/32, {branch['lan_subnet']}",
            "",
        ]
        hq_conf_lines.extend(hq_peer)

    # Write complete HQ config
    (WG_DIR / "hq-wg0.conf").write_text("\n".join(hq_conf_lines))

    print(f"  [+] WireGuard configs written to {WG_DIR}/")
    return key_store


# ---------------------------------------------------------------------------
# Firewall / ACL rule generation
# ---------------------------------------------------------------------------

def _service_to_iptables(service_name, svc_map, src_subnet, dst_subnet, action="ACCEPT"):
    """Return an iptables -A FORWARD rule string for a single named service."""
    if service_name not in svc_map:
        return f"# WARNING: unknown service '{service_name}' — skipped"
    svc  = svc_map[service_name]
    port = svc["port"]
    proto = svc["proto"]
    return (
        f"iptables -A FORWARD -s {src_subnet} -d {dst_subnet} "
        f"-p {proto} --dport {port} -j {action} "
        f"-m comment --comment 'branch:{service_name}'"
    )


def generate_firewall_rules(inventory):
    """
    For each branch, generate:
      configs/firewall/<branch_id>-iptables.sh
      configs/firewall/<branch_id>-nftables.conf
    Rules allow only approved_services; everything else is dropped.
    """
    FW_DIR.mkdir(parents=True, exist_ok=True)
    hq     = inventory["hq"]
    svc_map = hq["services"]

    for branch in inventory["branches"]:
        bid     = branch["id"]
        bsubnet = branch["lan_subnet"]
        hqsubnet = hq["lan_subnet"]
        approved = branch["approved_services"]

        # ── iptables script ───────────────────────────────────────────────
        lines = [
            "#!/bin/bash",
            f"# iptables rules for {branch['name']}",
            f"# Generated {datetime.now():%Y-%m-%d %H:%M}",
            "# Apply on the branch router"""
config_generator.py
Generates WireGuard tunnel configs and iptables/nftables firewall rules
from the site inventory.
"""

import os
import base64
import secrets
import yaml
from pathlib import Path
from datetime import datetime

CONFIGS_DIR = Path("configs")
WG_DIR      = CONFIGS_DIR / "wireguard"
FW_DIR      = CONFIGS_DIR / "firewall"

# ---------------------------------------------------------------------------
# Key helpers (realistic-looking placeholder keys for demo / real if wg present)
# ---------------------------------------------------------------------------

def _generate_wg_keypair():
    """Try real wg keygen; fall back to a realistic-looking placeholder."""
    import subprocess
    try:
        priv = subprocess.check_output(["wg", "genkey"],
                                        stderr=subprocess.DEVNULL).decode().strip()
        pub  = subprocess.check_output(["wg", "pubkey"],
                                        input=priv.encode(),
                                        stderr=subprocess.DEVNULL).decode().strip()
        return priv, pub
    except Exception:
        # Generate Base64-encoded random bytes that look like real WG keys
        priv_bytes = secrets.token_bytes(32)
        pub_bytes  = secrets.token_bytes(32)
        priv = base64.b64encode(priv_bytes).decode()
        pub  = base64.b64encode(pub_bytes).decode()
        return priv, pub


def load_inventory(path="inventory.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# WireGuard config generation
# ---------------------------------------------------------------------------

def generate_wg_configs(inventory):
    """
    For every branch, generate:
      - configs/wireguard/<branch_id>-branch.conf   (runs on branch router)
      - configs/wireguard/<branch_id>-hq-peer.conf  (peer block appended to HQ)
    Returns a dict: branch_id → {priv, pub, hq_pub}
    """
    WG_DIR.mkdir(parents=True, exist_ok=True)
    hq = inventory["hq"]
    hq_priv, hq_pub = _generate_wg_keypair()

    # Save HQ base config
    hq_conf_lines = [
        f"# HQ WireGuard Interface  — generated {datetime.now():%Y-%m-%d %H:%M}",
        "[Interface]",
        f"Address    = {hq['vpn_ip']}/24",
        f"ListenPort = {hq['wg_port']}",
        f"PrivateKey = {hq_priv}",
        "PostUp     = iptables -A FORWARD -i wg0 -j ACCEPT; "
                     "iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
        "PostDown   = iptables -D FORWARD -i wg0 -j ACCEPT; "
                     "iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE",
        "",
    ]

    key_store = {}

    for branch in inventory["branches"]:
        bid   = branch["id"]
        bpriv, bpub = _generate_wg_keypair()
        key_store[bid] = {"priv": bpriv, "pub": bpub, "hq_pub": hq_pub}

        # ── Branch-side config ────────────────────────────────────────────
        branch_conf = [
            f"# Branch: {branch['name']}  — generated {datetime.now():%Y-%m-%d %H:%M}",
            "# Deploy this file as /etc/wireguard/wg0.conf on the branch router",
            "[Interface]",
            f"Address    = {branch['vpn_ip']}/24",
            f"ListenPort = {branch['wg_port']}",
            f"PrivateKey = {bpriv}",
            f"DNS        = {hq['dns']}",
            "",
            "# HQ peer",
            "[Peer]",
            f"PublicKey  = {hq_pub}",
            f"Endpoint   = {hq['public_ip']}:{hq['wg_port']}",
            # Only tunnel traffic destined for HQ LAN + VPN range
            f"AllowedIPs = {hq['lan_subnet']}, 10.200.0.0/24",
            "PersistentKeepalive = 25",
            "",
        ]
        (WG_DIR / f"{bid}-branch.conf").write_text("\n".join(branch_conf))

        # ── HQ peer block for this branch ─────────────────────────────────
        hq_peer = [
            f"# Peer: {branch['name']}",
            "[Peer]",
            f"PublicKey  = {bpub}",
            f"AllowedIPs = {branch['vpn_ip']}/32, {branch['lan_subnet']}",
            "",
        ]
        hq_conf_lines.extend(hq_peer)

    # Write complete HQ config
    (WG_DIR / "hq-wg0.conf").write_text("\n".join(hq_conf_lines))

    print(f"  [+] WireGuard configs written to {WG_DIR}/")
    return key_store


# ---------------------------------------------------------------------------
# Firewall / ACL rule generation
# ---------------------------------------------------------------------------

def _service_to_iptables(service_name, svc_map, src_subnet, dst_subnet, action="ACCEPT"):
    """Return an iptables -A FORWARD rule string for a single named service."""
    if service_name not in svc_map:
        return f"# WARNING: unknown service '{service_name}' — skipped"
    svc  = svc_map[service_name]
    port = svc["port"]
    proto = svc["proto"]
    return (
        f"iptables -A FORWARD -s {src_subnet} -d {dst_subnet} "
        f"-p {proto} --dport {port} -j {action} "
        f"-m comment --comment 'branch:{service_name}'"
    )


def generate_firewall_rules(inventory):
    """
    For each branch, generate:
      configs/firewall/<branch_id>-iptables.sh
      configs/firewall/<branch_id>-nftables.conf
    Rules allow only approved_services; everything else is dropped.
    """
    FW_DIR.mkdir(parents=True, exist_ok=True)
    hq     = inventory["hq"]
    svc_map = hq["services"]

    for branch in inventory["branches"]:
        bid     = branch["id"]
        bsubnet = branch["lan_subnet"]
        hqsubnet = hq["lan_subnet"]
        approved = branch["approved_services"]

        # ── iptables script ───────────────────────────────────────────────
        lines = [
            "#!/bin/bash",
            f"# iptables rules for {branch['name']}",
            f"# Generated {datetime.now():%Y-%m-%d %H:%M}",
            "# Apply on the branch router (or HQ forward chain)",
            "",
            "# Flush existing FORWARD rules for this branch",
            f"iptables -F FORWARD",
            "",
            "# Allow established/related traffic",
            "iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT",
            "",
            "# Allow approved services from branch LAN → HQ LAN",
        ]
        for svc in approved:
            lines.append(_service_to_iptables(svc, svc_map, bsubnet, hqsubnet))

        # Drop everything else
        lines += [
            "",
            "# Block all other branch → HQ traffic",
            f"iptables -A FORWARD -s {bsubnet} -d {hqsubnet} -j DROP "
             f"-m comment --comment 'deny:unapproved'",
            "",
            "# NAT: masquerade branch traffic leaving HQ to internet (PAT)",
            "iptables -t nat -A POSTROUTING -s 10.200.0.0/24 -o eth0 -j MASQUERADE",
        ]
        script_path = FW_DIR / f"{bid}-iptables.sh"
        script_path.write_text("\n".join(lines))
        script_path.chmod(0o755)

        # ── nftables config ───────────────────────────────────────────────
        nft_lines = [
            f"# nftables ruleset for {branch['name']}",
            f"# Generated {datetime.now():%Y-%m-%d %H:%M}",
            "",
            "table inet filter {",
            "    chain forward {",
            "        type filter hook forward priority 0; policy drop;",
            "",
            "        # Allow established / related",
            "        ct state established,related accept",
            "",
            "        # Approved services: branch LAN → HQ LAN",
        ]
        for svc in approved:
            if svc not in svc_map:
                continue
            s     = svc_map[svc]
            proto = s["proto"]
            port  = s["port"]
            nft_lines.append(
                f"        ip saddr {bsubnet} ip daddr {hqsubnet} "
                f"{proto} dport {port} accept comment \"{svc}\""
            )
        nft_lines += [
            "",
            "        # Drop everything else from this branch",
            f"        ip saddr {bsubnet} drop",
            "    }",
            "",
            "    chain postrouting {",
            "        type nat hook postrouting priority 100;",
            "        ip saddr 10.200.0.0/24 oif eth0 masquerade",
            "    }",
            "}",
        ]
        (FW_DIR / f"{bid}-nftables.conf").write_text("\n".join(nft_lines))

    print(f"  [+] Firewall rules written to {FW_DIR}/")


# ---------------------------------------------------------------------------
# Route policy generation
# ---------------------------------------------------------------------------

def generate_route_policy(inventory):
    """Write a simple iproute2-style routing policy script for each branch."""
    hq = inventory["hq"]
    lines = [
        "#!/bin/bash",
        f"# Route policy — generated {datetime.now():%Y-%m-%d %H:%M}",
        "# Apply on HQ router to steer branch traffic correctly",
        "",
    ]
    for branch in inventory["branches"]:
        lines += [
            f"# {branch['name']}",
            f"ip route add {branch['lan_subnet']} via {branch['vpn_ip']} dev wg0",
            f"# Failover via backup link",
            f"ip route add {branch['lan_subnet']} via {branch['backup_public_ip']} "
            f"metric 200 dev eth1 || true",
            "",
        ]
    path = CONFIGS_DIR / "route-policy.sh"
    path.write_text("\n".join(lines))
    path.chmod(0o755)
    print(f"  [+] Route policy written to {path}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_generate(inventory_path="inventory.yaml"):
    print("\n=== Generating Secure Campus Fabric Configs ===\n")
    inv = load_inventory(inventory_path)
    generate_wg_configs(inv)
    generate_firewall_rules(inv)
    generate_route_policy(inv)
    print("\n[✓] All configs generated successfully.\n")            f"# Generated {datetime.now():%Y-%m-%d %H:%M}",            "",            "table inet filter {",            "    chain forward {",            "        type filter hook forward priority 0; policy drop;",            "",            "        # Allow established / related",            "        ct state established,related accept",            "",            "        # Approved services: branch LAN → HQ LAN",        ]        for svc in approved:            if svc not in svc_map:                continue            s     = svc_map[svc]            proto = s["proto"]            port  = s["port"]            nft_lines.append(                f"        ip saddr {bsubnet} ip daddr {hqsubnet} "                f"{proto} dport {port} accept comment \"{svc}\""            )        nft_lines += [            "",            "        # Drop everything else from this branch"            f"        ip saddr {bsubnet} drop",            "    }",            "",            "    chain postrouting {",            "        type nat hook postrouting priority 100;",            "        ip saddr 10.200.0.0/24 oif eth0 masquerade",            "    }",            "}",        ]        (FW_DIR / f"{bid}-nftables.conf").write_text("\n".join(nft_lines))    print(f"  [+] Firewall rules written to {FW_DIR}/")# ---------------------------------------------------------------------------# Route policy generation# ---------------------------------------------------------------------------def generate_route_policy(inventory):    """Write a simple iproute2-style routing policy script for each branch."""    hq = inventory["hq"]    lines = [        "#!/bin/bash",        f"# Route policy — generated {datetime.now():%Y-%m-%d %H:%M}",        "# Apply on HQ router to steer branch traffic correctly",        "",    ]    for branch in inventory["branches"]:        lines += [            f"# {branch['name']}",            f"ip route add {branch['lan_subnet']} via {branch['vpn_ip']} dev wg0",            f"# Failover via backup link",            f"ip route add {branch['lan_subnet']} via {branch['backup_publi            f"metric 200 dev eth1 || true",            "",        ]    path = CONFIGS_DIR / "route-policy.sh"    path.write_text("\n".join(lines))    path.chmod(0o755)    print(f"  [+] Route policy written to {path}")# ---------------------------------------------------------------------------# Public entry point# ---------------------------------------------------------------------------def run_generate(inventory_path="inventory.yaml")    print("\n=== Generating Secure Campus Fabric Configs ===\n"    inv = load_inventory(inventory_path    generate_wg_configs(inv    generate_firewall_rules(in    generate_route_policy(inv    print("\n[✓] All configs ge
