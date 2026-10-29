#!/usr/bin/env python3
"""
router_ctl.py - Command Line Management & Telemetry for ZTE ZXHN F670L

Queries the router web API for real-time status:
- Gateway uptime, CPU utilization, RAM usage, board temperature
- GPON optical signal metrics (Rx power, Tx power, registration state)
- Connected LAN & Wi-Fi client discovery (IP, MAC, hostname, RSSI)
- Wi-Fi radio configurations & channel utilization

Usage:
  ./scripts/router_ctl.py status
  ./scripts/router_ctl.py who
  ./scripts/router_ctl.py wifi
  ./scripts/router_ctl.py --host 192.168.1.1 status

License: MIT
"""

import sys
import os
import argparse
import hashlib
import subprocess
import requests
import urllib3
import re
import xml.etree.ElementTree as ET

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LIB_DIR = os.path.join(BASE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from zte_unlock import resolve_credentials

class RouterCtl:
    def __init__(self, host="192.168.1.1", user=None, password=None):
        self.host = host
        self.base_url = f"https://{host}"
        self.user = user
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
            "Referer": f"{self.base_url}/",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.base_url
        })

    def login(self):
        candidates = resolve_credentials(self.user, self.password)
        if not candidates:
            u = input("Enter router username [admin]: ").strip() or "admin"
            p = input("Enter router password: ").strip()
            candidates = [(u, p)]

        for user, pwd in candidates:
            try:
                r1 = self.session.get(f"{self.base_url}/?_type=loginData&_tag=login_entry", timeout=4)
                if r1.status_code != 200:
                    continue
                sess_token = r1.json().get("sess_token")

                r2 = self.session.get(f"{self.base_url}/?_type=loginData&_tag=login_token", timeout=4)
                m = re.search(r"<ajax_response_xml_root>(.*?)</ajax_response_xml_root>", r2.text)
                if not m:
                    continue
                salt = m.group(1).strip()

                hashed_pwd = hashlib.sha256((pwd + salt).encode("utf-8")).hexdigest()
                payload = {
                    "action": "login",
                    "Username": user,
                    "Password": hashed_pwd,
                    "_sessionTOKEN": sess_token
                }
                r3 = self.session.post(f"{self.base_url}/?_type=loginData&_tag=login_entry", data=payload, timeout=4)
                if r3.status_code == 200 and r3.json().get("login_need_refresh"):
                    self.session.get(f"{self.base_url}/", timeout=4)
                    return True
            except Exception:
                pass

        print(f"[-] Authentication failed with gateway at {self.host}.", file=sys.stderr)
        return False

    def get_data(self, menu_id):
        view_url = f"{self.base_url}/?_type=menuView&_tag={menu_id}&Menu3Location=0"
        headers = {"Referer": view_url}
        r_view = self.session.get(view_url, headers=headers)
        if r_view.status_code != 200:
            return {}

        m_tok = re.search(r'_sessionTmpToken\s*=\s*"([^"]+)"', r_view.text)
        if not m_tok:
            return {}
        tok = m_tok.group(1).encode("utf-8").decode("unicode_escape")
        headers["X-Requested-With"] = "XMLHttpRequest"

        results = {}
        for action in re.findall(r'<span class="form-action">(/[^<]+)</span>', r_view.text):
            ep = f"{self.base_url}{action}&_sessionTOKEN={tok}"
            r_data = self.session.get(ep, headers=headers)
            if r_data.status_code == 200:
                results[action] = self._parse_xml(r_data.text)
        return results

    def _parse_xml(self, xml_text):
        try:
            root = ET.fromstring(xml_text)
            data = {}
            for obj in root:
                tag = obj.tag
                if tag.startswith("IF_"):
                    data[tag] = obj.text
                    continue
                instances = []
                for inst in obj.findall("Instance"):
                    item = {}
                    paras = inst.findall("ParaName")
                    vals = inst.findall("ParaValue")
                    for p, v in zip(paras, vals):
                        item[p.text] = v.text
                    instances.append(item)
                data[tag] = instances
            return data
        except Exception:
            return {}

def cmd_status(ctl):
    sys_data = ctl.get_data("statusMgr")
    status_menu = sys_data.get("/?_type=menuData&_tag=devmgr_statusmgr_lua.lua", {})
    dev = status_menu.get("OBJ_DEVINFO_ID", [{}])[0]
    cpu = status_menu.get("OBJ_CPUMEMUSAGE_ID", [{}])[0]
    pwr = status_menu.get("OBJ_POWERONTIME_ID", [{}])[0]

    pon_data = ctl.get_data("ponopticalinfo")
    pon_addr = "/?_type=menuData&_tag=optical_info_lua.lua"
    pon_para = pon_data.get(pon_addr, {}).get("OBJ_PON_OPTICALPARA_ID", [{}])[0]
    gpon_reg = pon_data.get(pon_addr, {}).get("OBJ_GPONREGSTATUS_ID", [{}])[0]

    uptime_sec = int(pwr.get("PowerOnTime", "0"))
    days = uptime_sec // 86400
    hours = (uptime_sec % 86400) // 3600
    mins = (uptime_sec % 3600) // 60
    uptime_str = f"{days}d {hours}h {mins}m" if days > 0 else f"{hours}h {mins}m"

    print("\n=== ZTE ZXHN F670L Gateway Status ===")
    print(f"  Model:            {dev.get('ModelName', 'ZXHN F670L')} (Hardware: {dev.get('HardwareVer', 'V9.0')})")
    print(f"  Firmware:         {dev.get('SoftwareVer', 'N/A')}")
    print(f"  Uptime:           {uptime_str}")
    print(f"  CPU Utilization:  Core 1: {cpu.get('CpuUsage1', '0')}%, Core 2: {cpu.get('CpuUsage2', '0')}%")
    print(f"  RAM Usage:        {cpu.get('MemUsage', '0')}%")
    print(f"  Board Temp:       {pon_para.get('Temp', 'N/A')} °C")
    print("\n--- GPON Optical Link ---")
    print(f"  Rx Optical Power: {pon_para.get('RxPower', 'N/A')} dBm (Healthy range: -8 to -27 dBm)")
    print(f"  Tx Optical Power: {pon_para.get('TxPower', 'N/A')} dBm")
    print(f"  Optical Status:   {'Active & Operational' if gpon_reg.get('RegStatus') == '5' else 'Down / Training'}\n")

def cmd_who(ctl):
    net_data = ctl.get_data("landevmgr")
    lan_data = net_data.get("/?_type=menuData&_tag=accessdev_landevs_lua.lua", {}).get("OBJ_ACCESSDEV_ID", [])

    wlan_ad = ctl.get_data("wlanclient")
    wlan_data = wlan_ad.get("/?_type=menuData&_tag=wlan_client_stat_lua.lua", {}).get("OBJ_WLAN_AD_ID", [])
    wlan_map = {c.get("MACAddress", "").lower(): c for c in wlan_data}

    print("\n=== Connected Devices ===")
    print(f"{'Hostname':<22} {'IP Address':<16} {'MAC Address':<18} {'Type':<8} {'Signal'}")
    print("-" * 72)
    for d in lan_data:
        mac = d.get("MACAddress", "").lower()
        ip = d.get("IPAddress", "")
        name = d.get("HostName", "Unknown") or "Unknown"
        is_wifi = mac in wlan_map
        itype = "Wi-Fi" if is_wifi else "Ethernet"
        sig = f"{wlan_map[mac].get('RSSI', 'N/A')} dBm" if is_wifi else "-"
        print(f"{name[:20]:<22} {ip:<16} {mac.upper():<18} {itype:<8} {sig}")
    print("-" * 72 + "\n")

def cmd_wifi(ctl):
    wlan = ctl.get_data("wlanbasicadconf")
    settings = wlan.get("/?_type=menuData&_tag=wlan_wlanbasicadconf_lua.lua", {}).get("OBJ_WLANSETTING_ID", [])
    print("\n=== Wi-Fi Radio Status ===")
    for s in settings:
        inst = s.get("_InstID", "")
        band = "2.4 GHz" if "WLAN1" in inst else "5 GHz"
        status = "Enabled" if s.get("RadioStatus") == "1" else "Disabled"
        print(f"  Radio: {band} ({inst})")
        print(f"    Status:         {status}")
        print(f"    Standard:       {s.get('Standard')}")
        print(f"    Channel:        {s.get('Channel')} (Bandwidth: {s.get('BandWidth')})")
        print(f"    Transmit Power: {s.get('TransPower', '100')}%\n")

def main():
    parser = argparse.ArgumentParser(description="ZTE ZXHN F670L CLI Control & Telemetry")
    parser.add_argument("action", choices=["status", "who", "wifi"], help="Action to execute")
    parser.add_argument("--host", default=os.environ.get("ROUTER_IP", "192.168.1.1"), help="Router IP")
    parser.add_argument("--user", default=os.environ.get("ROUTER_USER", ""), help="Web username")
    parser.add_argument("--password", default=os.environ.get("ROUTER_PASS", ""), help="Web password")
    args = parser.parse_args()

    ctl = RouterCtl(host=args.host, user=args.user, password=args.password)
    if not ctl.login():
        sys.exit(1)

    if args.action == "status":
        cmd_status(ctl)
    elif args.action == "who":
        cmd_who(ctl)
    elif args.action == "wifi":
        cmd_wifi(ctl)

if __name__ == "__main__":
    main()
