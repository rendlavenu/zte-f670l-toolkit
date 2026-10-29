#!/usr/bin/env python3
"""
extract_credentials.py - Automated Credential Extractor for ZTE ZXHN F670L

Connects via the factory root Telnet session and extracts:
- PPPoE WAN credentials (Username & Plaintext Password)
- VoIP / SIP Landline credentials (DID, SIP User, Password, Registrar, Outbound Proxy)
- GPON Optical provisioning tokens (Serial Number ASCII & Hex, SLID / PLOAM Password, LOID)
- Wi-Fi Radio configurations (SSID names and WPA2/WPA3 pre-shared keys)

Usage:
  ./scripts/extract_credentials.py
  ./scripts/extract_credentials.py --json > credentials.json
  ./scripts/extract_credentials.py --host 192.168.1.1 --user admin --password secret

License: MIT
"""

import sys
import os
import re
import time
import socket
import json
import argparse
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LIB_DIR = os.path.join(BASE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from zte_unlock import attempt_unlock, resolve_credentials

def telnet_session(host, user, pw):
    """Establish Telnet connection using temporary session credentials."""
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

    prompt = read_until(b"/ # ")
    if b"/ # " not in prompt:
        raise RuntimeError("Failed to obtain root shell prompt.")

    return s

def run_cmd(s, command):
    """Execute command in BusyBox shell and return output."""
    s.sendall(command.encode() + b"\r\n")
    buf = b""
    while b"/ # " not in buf:
        chunk = s.recv(2048)
        if not chunk: break
        buf += chunk
    out = buf.decode("utf-8", errors="ignore")
    # Clean command echo and trailing prompt
    lines = out.splitlines()
    if lines and command in lines[0]:
        lines = lines[1:]
    if lines and "/ #" in lines[-1]:
        lines = lines[:-1]
    return "\n".join(lines).strip()

def parse_db_table(raw_output):
    """Parse ZTE sendcmd DB table dump into a list of key-value dictionaries."""
    entries = []
    current = {}
    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("<") and line.endswith(">") and "/" not in line:
            if current:
                entries.append(current)
                current = {}
            continue
        m = re.match(r"<([^>]+)>(.*?)</\1>", line)
        if m:
            current[m.group(1)] = m.group(2)
        else:
            m2 = re.match(r"^(\w+)\s*=\s*(.+)$", line)
            if m2:
                current[m2.group(1)] = m2.group(2)
    if current:
        entries.append(current)
    return entries

def extract_all(host, web_user, web_pass):
    ok, res = False, ""
    for attempt in range(1, 4):
        ok, res = attempt_unlock(web_user, web_pass, host=host)
        if ok:
            break
        time.sleep(1.5)

    if not ok:
        raise RuntimeError(f"Factory mode handshake failed for user '{web_user}': {res}")

    parsed = parse_qs(urlparse(res).query)
    t_user = parsed.get("user", [""])[0]
    t_pass = parsed.get("pass", [""])[0]

    s = telnet_session(host, t_user, t_pass)
    data = {}

    try:
        # 1. Device Info
        dev_info = run_cmd(s, "sendcmd 1 DB p DevInfo")
        dev_parsed = parse_db_table(dev_info)
        if dev_parsed:
            d = dev_parsed[0]
            data["device"] = {
                "model": d.get("ModelName") or d.get("ProductClass", "ZXHN F670L"),
                "software_version": d.get("SoftwareVer", ""),
                "hardware_version": d.get("HardwareVer", ""),
                "serial_number": d.get("SerialNumber", "")
            }

        # 2. PPPoE WAN
        ppp_info = run_cmd(s, "sendcmd 1 DB p PPPIF")
        ppp_parsed = parse_db_table(ppp_info)
        data["pppoe"] = []
        for p in ppp_parsed:
            user = p.get("Username", "")
            if user:
                data["pppoe"].append({
                    "username": user,
                    "password": p.get("Password", ""),
                    "vlan_id": 100,
                    "service_name": p.get("ServiceName", "Internet")
                })

        # 3. VoIP SIP
        sip_line = run_cmd(s, "sendcmd 1 DB p VoIPSIPLine")
        sip_server = run_cmd(s, "sendcmd 1 DB p VoIPSIPServer")
        line_parsed = parse_db_table(sip_line)
        srv_parsed = parse_db_table(sip_server)

        proxy = srv_parsed[0].get("OutBoundProxy", "") if srv_parsed else ""
        domain = srv_parsed[0].get("RegistrarServer", "") if srv_parsed else ""
        if not domain and srv_parsed:
            domain = srv_parsed[0].get("DomainName", "ims.airtel.in")

        data["voip_sip"] = []
        for l in line_parsed:
            did = l.get("DirectoryNumber", "")
            if did:
                data["voip_sip"].append({
                    "did_number": did,
                    "username": l.get("AuthUserName") or l.get("URI", ""),
                    "password": l.get("AuthPassword", ""),
                    "domain": domain,
                    "outbound_proxy": proxy
                })

        # 4. GPON Optical Provisioning
        gpon_info = run_cmd(s, "sendcmd 1 DB p GPON")
        gpon_parsed = parse_db_table(gpon_info)
        sn_ascii = gpon_parsed[0].get("GponSN", "") if gpon_parsed else ""
        sn_hex = sn_ascii.encode("utf-8").hex().upper() if sn_ascii else ""

        tag_mac = run_cmd(s, "cat /sys/class/net/br0/address 2>/dev/null || cat /sys/class/net/eth0/address")
        data["gpon"] = {
            "vendor_id": sn_ascii[:4] if len(sn_ascii) >= 4 else "ZTEG",
            "gpon_sn_ascii": sn_ascii,
            "gpon_sn_hex": sn_hex,
            "slid_ploam_password": gpon_parsed[0].get("Passwd", "") if gpon_parsed else "",
            "loid": gpon_parsed[0].get("LOID", "") if gpon_parsed else "",
            "loid_password": gpon_parsed[0].get("LOIDPasswd", "") if gpon_parsed else "",
            "base_mac": tag_mac.strip()
        }

        # 5. Wi-Fi Radios
        wlan_info = run_cmd(s, "sendcmd 1 DB p WLANBase")
        wlan_parsed = parse_db_table(wlan_info)
        data["wifi"] = []
        for w in wlan_parsed:
            ssid = w.get("ESSID", "")
            if ssid:
                data["wifi"].append({
                    "ssid": ssid,
                    "password": w.get("WpaPsk", ""),
                    "security": w.get("BeaconType", "WPA2-PSK")
                })

    finally:
        s.close()

    return data

def main():
    parser = argparse.ArgumentParser(description="Extract Credentials from ZTE ZXHN F670L")
    parser.add_argument("--host", default=os.environ.get("ROUTER_IP", "192.168.1.1"), help="Router IP")
    parser.add_argument("--user", default=os.environ.get("ROUTER_USER", ""), help="Web username")
    parser.add_argument("--password", default=os.environ.get("ROUTER_PASS", ""), help="Web password")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    candidates = resolve_credentials(args.user, args.password)
    if not candidates:
        user = input("Enter web username [admin]: ").strip() or "admin"
        pw = input("Enter web password: ").strip()
        candidates = [(user, pw)]

    if not args.json:
        print(f"[*] Extracting credentials from {args.host}...")

    data = None
    last_err = ""
    for u, p in candidates:
        try:
            data = extract_all(args.host, u, p)
            if data:
                break
        except Exception as e:
            last_err = str(e)
            time.sleep(1)

    if not data:
        print(f"[-] Extraction failed: {last_err}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    print("\n" + "=" * 60)
    print("         ZTE ZXHN F670L CREDENTIAL EXTRACTION REPORT        ")
    print("=" * 60)

    dev = data.get("device", {})
    print(f"\n[+] Hardware: {dev.get('model')} | Firmware: {dev.get('software_version')}")
    print(f"    Serial:   {dev.get('serial_number')}")

    print("\n--- PPPoE WAN Internet Authentication ---")
    for p in data.get("pppoe", []):
        print(f"  Username: {p['username']}")
        print(f"  Password: {p['password']}")
        print(f"  VLAN ID:  {p['vlan_id']}")

    print("\n--- VoIP SIP Telephony (Landline) ---")
    for s in data.get("voip_sip", []):
        print(f"  Landline Number: {s['did_number']}")
        print(f"  Auth Username:   {s['username']}")
        print(f"  Auth Password:   {s['password']}")
        print(f"  Registrar:       {s['domain']}")
        print(f"  Outbound Proxy:  {s['outbound_proxy']}")

    gpon = data.get("gpon", {})
    print("\n--- GPON Optical Provisioning (ONT Cloning) ---")
    print(f"  GPON SN (ASCII): {gpon.get('gpon_sn_ascii')}")
    print(f"  GPON SN (HEX):   {gpon.get('gpon_sn_hex')}")
    print(f"  SLID / PLOAM:    {gpon.get('slid_ploam_password') or '(None / Default)'}")
    print(f"  LOID:            {gpon.get('loid') or '(None)'}")
    print(f"  Base MAC:        {gpon.get('base_mac')}")

    print("\n--- Wi-Fi Radios ---")
    for w in data.get("wifi", []):
        print(f"  SSID: {w['ssid']:<24} Key: {w['password']}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
