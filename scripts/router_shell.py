#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
router_shell.py - Interactive Root Shell Connector for ZTE ZXHN F670L

Authenticates via /webFac factory handshake, establishes Telnet session on port 23,
and opens an interactive root BusyBox ash shell (/ # ).

Usage:
  ./scripts/router_shell.py
  ./scripts/router_shell.py --host 192.168.1.1 --user admin --password secret
  ROUTER_PASS=secret ./scripts/router_shell.py

Disclaimer: For authorized device administration, research, and personal equipment only.
"""

import sys
import os
import time
import socket
import select
import termios
import tty
import argparse
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LIB_DIR = os.path.join(BASE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from zte_unlock import attempt_unlock, resolve_credentials

def main():
    parser = argparse.ArgumentParser(description="ZTE ZXHN F670L Interactive Root Shell")
    parser.add_argument("--host", default=os.environ.get("ROUTER_IP", "192.168.1.1"), help="Router IP address")
    parser.add_argument("--user", default=os.environ.get("ROUTER_USER", ""), help="Web admin username")
    parser.add_argument("--password", default=os.environ.get("ROUTER_PASS", ""), help="Web admin password")
    args = parser.parse_args()

    host = args.host
    candidates = resolve_credentials(args.user, args.password)
    if not candidates:
        user = input("Enter web username [admin]: ").strip() or "admin"
        pw = input("Enter web password: ").strip()
        candidates = [(user, pw)]

    ok, res = False, ""
    for user, pw in candidates:
        print(f"[*] Authenticating with router at {host} as '{user}'...")
        for attempt in range(1, 3):
            ok, res = attempt_unlock(user, pw, host=host)
            if ok:
                break
            time.sleep(1)
        if ok:
            break

    if not ok:
        print(f"[-] FATAL: Factory handshake failed: {res}", file=sys.stderr)
        print("    Ensure your PC is connected directly to a LAN port or Wi-Fi of the F670L.", file=sys.stderr)
        sys.exit(1)

    parsed = parse_qs(urlparse(res).query)
    telnet_user = parsed.get("user", [""])[0]
    telnet_pw = parsed.get("pass", [""])[0]

    if not telnet_user or not telnet_pw:
        print("[-] Error: Failed to parse temporary session credentials.", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Factory mode active! Connecting to Telnet port 23 (session user: {telnet_user})...")
    try:
        s = socket.create_connection((host, 23), timeout=5)
    except Exception as e:
        print(f"[-] Failed to connect to {host}:23: {e}", file=sys.stderr)
        sys.exit(1)

    # Handshake Telnet Login
    buf = b""
    while b"Login:" not in buf:
        chunk = s.recv(1024)
        if not chunk: break
        buf += chunk
    s.sendall(telnet_user.encode() + b"\r\n")

    buf = b""
    while b"Password:" not in buf:
        chunk = s.recv(1024)
        if not chunk: break
        buf += chunk
    s.sendall(telnet_pw.encode() + b"\r\n")

    buf = b""
    while b"/ # " not in buf:
        chunk = s.recv(1024)
        if not chunk: break
        buf += chunk
        if b"Access denied" in buf or b"Login incorrect" in buf:
            print("[-] Access denied by router Telnet daemon.", file=sys.stderr)
            sys.exit(1)

    print("\n" + "=" * 56)
    print("  CONNECTED: ZTE ZXHN F670L ROOT BUSYBOX SHELL (/ #)")
    print("  Type 'exit' to disconnect.")
    print("=" * 56 + "\n")

    is_tty = sys.stdin.isatty()
    old_tty = None
    if is_tty:
        old_tty = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

    try:
        s.setblocking(False)
        sys.stdout.write(buf.decode("utf-8", errors="ignore"))
        sys.stdout.flush()

        while True:
            rlist, _, _ = select.select([sys.stdin, s], [], [])
            if sys.stdin in rlist:
                data = sys.stdin.buffer.read(1024)
                if not data:
                    break
                s.sendall(data)
            if s in rlist:
                data = s.recv(4096)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.flush()
    except Exception:
        pass
    finally:
        if old_tty:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        s.close()
        print("\n[*] Disconnected from router shell.")

if __name__ == "__main__":
    main()
