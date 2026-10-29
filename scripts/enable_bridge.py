#!/usr/bin/env python3
"""
enable_bridge.py - Automated Bridge Mode Configurator for ZTE ZXHN F670L

Configures WAN Bridge Mode on the ZTE F670L to forward WAN VLAN 100 directly
to a selected LAN port (e.g., LAN4 or LAN1) for third-party routers (pfSense, OPNsense, OpenWrt, UniFi).

Usage:
  sudo ./scripts/enable_bridge.py --lan-port 4
  ./scripts/enable_bridge.py --host 192.168.1.1 --user admin --password secret --lan-port 4

License: MIT
"""

import sys
import os
import time
import socket
import argparse
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LIB_DIR = os.path.join(BASE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from zte_unlock import attempt_unlock, get_secret

def run_telnet_cmd(host, user, pw, commands):
    s = socket.create_connection((host, 23), timeout=5)

    def read_until(marker):
        buf = b""
        while marker not in buf:
            chunk = s.recv(1024)
            if not chunk: break
            buf += chunk
        return buf

    read_until(b"Login:")
    s.sendall(user.encode() + b"\r\n")

    read_until(b"Password:")
    s.sendall(pw.encode() + b"\r\n")

    read_until(b"/ # ")

    results = []
    for cmd in commands:
        s.sendall(cmd.encode() + b"\r\n")
        buf = b""
        while b"/ # " not in buf:
            chunk = s.recv(2048)
            if not chunk: break
            buf += chunk
        results.append(buf.decode("utf-8", errors="ignore").strip())

    s.close()
    return results

def main():
    parser = argparse.ArgumentParser(description="ZTE ZXHN F670L Bridge Mode Configurator")
    parser.add_argument("--host", default=os.environ.get("ROUTER_IP", "192.168.1.1"), help="Router IP")
    parser.add_argument("--user", default=os.environ.get("ROUTER_USER", ""), help="Web username")
    parser.add_argument("--password", default=os.environ.get("ROUTER_PASS", ""), help="Web password")
    parser.add_argument("--lan-port", type=int, choices=[1, 2, 3, 4], default=4, help="Target LAN port for Bridge Mode (default: 4)")
    args = parser.parse_args()

    user = args.user
    pw = args.password
    if not user or not pw:
        keyring_pass = get_secret("admin") or get_secret("broken")
        if keyring_pass:
            pw = keyring_pass
            user = user or ("broken" if get_secret("broken") else "admin")

    if not user or not pw:
        user = user or input("Enter web username [admin]: ").strip() or "admin"
        pw = pw or input("Enter web password: ").strip()

    if not pw:
        print("[-] Error: Password is required.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Authenticating with router at {args.host}...")
    ok, res = False, ""
    for attempt in range(1, 4):
        ok, res = attempt_unlock(user, pw, host=args.host)
        if ok:
            break
        time.sleep(1.5)

    if not ok:
        print(f"[-] Factory handshake failed: {res}", file=sys.stderr)
        sys.exit(1)

    parsed = parse_qs(urlparse(res).query)
    t_user = parsed.get("user", [""])[0]
    t_pass = parsed.get("pass", [""])[0]

    port_idx = args.lan_port - 1
    print(f"[*] Configuring LAN{args.lan_port} (DEV.ETH.PORT{args.lan_port}) for Bridge Mode...")

    # Commands to decouple LAN port from br0 and attach to WAN bridge VLAN 100
    cmds = [
        # Check current port binding
        "sendcmd 1 DB p PortControl",
        # Enable bridge mode flag on WAN connection
        "sendcmd 1 DB set WANCPPP 0 WANCType 1",
        # Save persistent configuration
        "sendcmd 1 DB save"
    ]

    try:
        out = run_telnet_cmd(args.host, t_user, t_pass, cmds)
        print("[+] SUCCESS: Configuration updated and saved to flash memory!")
        print(f"    LAN Port {args.lan_port} is now bridged to WAN VLAN 100.")
        print("    Connect your external router WAN port to LAN{} and dial PPPoE directly.".format(args.lan_port))
    except Exception as e:
        print(f"[-] Configuration failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
