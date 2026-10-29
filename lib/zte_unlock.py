#!/usr/bin/env python3
"""
zte_unlock.py - Cryptographic Challenge-Response Engine for ZTE ZXHN F670L

Authenticates against ZTE's hidden /webFac and /webFacEntry endpoints:
1. Resets the factory session (POST /webFac SendSq.gch).
2. Requests factory challenge parameters (POST /webFac RequestFactoryMode.gch & SendSq.gch?rand=0).
3. Computes modular exponentiation payload aligning client MAC and router MAC.
4. Derives 24-byte AES ECB key from KEY_POOL offset.
5. Exchanges encrypted handshake with /webFacEntry (SendInfo.gch & CheckLoginAuth.gch).
6. Requests mode 2 factory elevation (FactoryMode.gch?mode=2), receiving temporary root credentials.

License: MIT
"""

import sys
import os
import re
import subprocess
from urllib.parse import urlparse, parse_qs

try:
    from Crypto.Cipher import AES
except ImportError:
    try:
        from Cryptodome.Cipher import AES
    except ImportError:
        print("[-] Error: pycryptodome is required. Run: pip install pycryptodome", file=sys.stderr)
        sys.exit(1)

import requests

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from rss import create_payload_array, verify_do_check_client, parse_mac

def get_secret(key="admin"):
    """Lookup password from environment or secret-tool keyring."""
    env_pass = os.environ.get("ROUTER_PASS")
    if env_pass:
        return env_pass
    for k in [key, "broken", "admin"]:
        try:
            res = subprocess.check_output(
                ["secret-tool", "lookup", "service", "router", "username", k],
                text=True, stderr=subprocess.DEVNULL
            )
            if res.strip():
                return res.strip()
        except Exception:
            pass
    return None

def resolve_credentials(user=None, password=None):
    """Return a list of candidate (username, password) tuples to try."""
    if user and password:
        return [(user, password)]

    candidates = []
    # Check environment variables
    env_user = os.environ.get("ROUTER_USER")
    env_pass = os.environ.get("ROUTER_PASS")
    if env_user and env_pass:
        candidates.append((env_user, env_pass))

    # Check secret-tool keyring
    for u in ["broken", "admin"]:
        try:
            res = subprocess.check_output(
                ["secret-tool", "lookup", "service", "router", "username", u],
                text=True, stderr=subprocess.DEVNULL
            )
            if res.strip():
                candidates.append((u, res.strip()))
        except Exception:
            pass

    # Common factory defaults
    candidates.extend([
        ("admin", "admin"),
        ("admin", "zte521"),
        ("telecomadmin", "admintelecom"),
    ])
    return candidates

def get_active_mac(target_ip="192.168.1.1"):
    """Dynamically determine the local MAC address routing to target_ip."""
    try:
        out = subprocess.check_output(["ip", "route", "get", target_ip], text=True, stderr=subprocess.DEVNULL)
        m = re.search(r"dev\s+(\S+)", out)
        if m:
            iface = m.group(1)
            sysfs_path = f"/sys/class/net/{iface}/address"
            if os.path.exists(sysfs_path):
                with open(sysfs_path) as f:
                    mac = f.read().strip()
                    if len(mac) == 17:
                        return mac
    except Exception:
        pass

    # Try common interface names
    for iface in ["eth0", "wlan0", "enp79s0", "wlp80s0"]:
        try:
            out = subprocess.check_output(["ip", "link", "show", iface], text=True, stderr=subprocess.DEVNULL)
            m = re.search(r"link/ether\s+([0-9a-fA-F:]{17})", out)
            if m:
                return m.group(1)
        except Exception:
            pass

    return "00:11:22:33:44:55"

KEY_POOL = [
    0x9c, 0x33, 0x75, 0xd1, 0x1c, 0x42, 0x45, 0x37, 0x18, 0x48,
    0x91, 0x73, 0x17, 0x45, 0x79, 0x44, 0x43, 0xd7, 0xd5, 0x73,
    0x33, 0x54, 0x76, 0xd2, 0xc5, 0xf1, 0x2c, 0x4f, 0x7a, 0xba,
    0x61, 0xd9, 0x5c, 0x69, 0xdf, 0x8c, 0xd2, 0x1c, 0xde, 0x3b,
    0x35, 0x2d, 0x2f, 0xe1, 0xde, 0x4c, 0x77, 0xf5, 0x1a, 0x65,
    0xd1, 0xfe, 0x18, 0x43, 0x8e, 0xa7, 0x42, 0x08, 0x04, 0x78,
    0xd5, 0xe4, 0xf3, 0x34, 0xA4, 0xd3, 0xf2, 0x36, 0x47, 0x6d,
    0x86, 0x9d, 0x42, 0x65, 0x13, 0x42, 0xdc, 0x42, 0x99, 0x48,
    0xdc, 0x67, 0x9f, 0x9e, 0xdc, 0x46, 0x37, 0x5f, 0x84, 0x9f,
    0x6f, 0x76, 0xce, 0x79, 0x4f, 0x49,
]

def pad(data, block_size=16):
    padding_len = block_size - len(data) % block_size
    return data + b"\x00" * padding_len

def unpad(padded_data, block_size=16):
    return padded_data[:-block_size] + padded_data[-block_size:].rstrip(b"\x00")

def attempt_unlock(username, password, host="192.168.1.1", local_mac=None):
    """
    Executes the cryptographic factory challenge-response handshake.
    Returns (True, session_auth_url) on success, or (False, error_msg) on failure.
    """
    root_url = f"http://{host}"
    if not local_mac:
        local_mac = get_active_mac(host)

    local_mac_bytes = parse_mac(local_mac)

    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})

    # Reset
    try:
        res = s.post(f"{root_url}/webFac", data="SendSq.gch", timeout=5)
        if res.status_code != 400:
            return False, f"Reset failed: expected HTTP 400, got {res.status_code}"
    except Exception as e:
        return False, f"Connection to {host} failed: {e}"

    # Step 1: RequestFactoryMode
    try:
        s.post(f"{root_url}/webFac", data="RequestFactoryMode.gch", timeout=5)
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        return False, f"Step 1 failed: {e}"

    # Step 2: Query Challenge
    client_rand = 0
    try:
        res = s.post(f"{root_url}/webFac", data=f"SendSq.gch?rand={client_rand}\r\n", timeout=5)
        if res.status_code != 200:
            return False, f"Step 2 failed: status {res.status_code}"
    except Exception as e:
        return False, f"Step 2 failed: {e}"

    match = re.match(r"re_rand=([^&]+)&([^&]+)&([^&]+)", res.text)
    if not match:
        return False, f"Step 2 failed: pattern mismatch '{res.text}'"

    server_rand, rand_seed_trunc, server_mac_bytes = match.groups()
    server_rand = int(server_rand)
    server_mac = server_mac_bytes.encode("latin-1")

    # Step 3: Solve modular payload
    client_rand_mix = (0x1000193 * client_rand)
    client_rand_mask = client_rand_mix & 0x8000003F
    client_xor_server = client_rand_mask ^ server_rand
    index = client_xor_server % 60

    aes_key = bytes(map(lambda x: (x ^ 0xA5) & 0xFF, KEY_POOL[index : index + 24]))
    aes = AES.new(aes_key, AES.MODE_ECB)

    payload_arr = create_payload_array(server_mac, local_mac_bytes, index)
    if not verify_do_check_client(payload_arr, local_mac_bytes, index, server_mac):
        return False, "verify_do_check_client failed"

    encoded_chars = b"".join(map(lambda x: x.to_bytes(4, "little"), payload_arr)).decode("utf-8")
    payload = f"SendInfo.gch?info={len(payload_arr)}|{encoded_chars}"

    res = s.post(f"{root_url}/webFacEntry", data=aes.encrypt(pad(payload.encode(), 16)), timeout=5)
    if res.status_code != 200:
        return False, f"Step 3 SendInfo failed: {res.status_code}"

    # Step 4: CheckLoginAuth
    auth_payload = f"CheckLoginAuth.gch?version50&user={username}&pass={password}"
    res = s.post(f"{root_url}/webFacEntry", data=aes.encrypt(pad(auth_payload.encode(), 16)), timeout=5)
    if res.status_code != 200:
        return False, f"Step 4 CheckLoginAuth failed: {res.status_code}"

    content = res.content
    if len(content) % 16:
        content = pad(content, 16)
    res_url = unpad(aes.decrypt(content), 16)
    if b"FactoryMode.gch" not in res_url:
        return False, f"Step 4 unexpected response: {res_url}"

    # Step 5: FactoryMode elevation
    fm_payload = "FactoryMode.gch?mode=2&user=notused"
    res = s.post(f"{root_url}/webFacEntry", data=aes.encrypt(pad(fm_payload.encode(), 16)), timeout=5)
    if res.status_code != 200:
        return False, f"Step 5 failed: {res.status_code}"

    fm_content = res.content
    if len(fm_content) % 16:
        fm_content = pad(fm_content, 16)
    decrypted = aes.decrypt(fm_content).rstrip(b"\x00").decode("utf-8", errors="ignore")
    return True, decrypted
