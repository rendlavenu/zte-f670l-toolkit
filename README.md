# ZTE ZXHN F670L Root & Management Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Target Hardware](https://img.shields.io/badge/Target-ZTE%20ZXHN%20F670L%20V9.0-blue.svg)](#)
[![Firmware](https://img.shields.io/badge/Firmware-V9.0.10P18N3D-brightgreen.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

Target-focused root exploit, credential extractor, and bridge mode configurator for the **ZTE ZXHN F670L GPON Gateway** (Hardware V9.0, firmware `V9.0.10P18N3D` and V9.0 variants, commonly deployed on Airtel Xstream Fiber).

Unlocks the factory diagnostic interface (`/webFac`) to provide root BusyBox shell access, extract locked carrier credentials, and configure true WAN Bridge Mode for third-party routers.

---

## ⚡ Quick Start

```bash
git clone https://github.com/rendlavenu/f670l-toolkit.git
cd f670l-toolkit
pip install -r requirements.txt

# 1. Spawn interactive root BusyBox ash shell (/ # )
./scripts/router_shell.py

# 2. Extract PPPoE, VoIP SIP, GPON SN, and Wi-Fi credentials
./scripts/extract_credentials.py

# 3. Enable true WAN Bridge Mode on LAN4 (for pfSense, OPNsense, UniFi, OpenWrt)
./scripts/enable_bridge.py --lan-port 4

# 4. Check real-time optical power (Rx/Tx dBm), CPU/RAM load, and connected devices
./scripts/router_ctl.py status
```

---

## 🛠 Core Tools

| Script | Command | Purpose |
| :--- | :--- | :--- |
| [`router_shell.py`](file:///home/broken/myWorld/f670l-toolkit/scripts/router_shell.py) | `./scripts/router_shell.py` | Solves `/webFac` challenge-response and opens an interactive root shell (`/ # `) via Telnet port 23. |
| [`extract_credentials.py`](file:///home/broken/myWorld/f670l-toolkit/scripts/extract_credentials.py) | `./scripts/extract_credentials.py [--json]` | Extracts plaintext PPPoE, SIP VoIP passwords, GPON SN (ASCII/Hex), SLID/PLOAM, and Wi-Fi keys from NVRAM. |
| [`enable_bridge.py`](file:///home/broken/myWorld/f670l-toolkit/scripts/enable_bridge.py) | `./scripts/enable_bridge.py --lan-port 4` | Binds WAN VLAN 100 directly to a physical LAN port to eliminate Double NAT on external routers. |
| [`router_ctl.py`](file:///home/broken/myWorld/f670l-toolkit/scripts/router_ctl.py) | `./scripts/router_ctl.py {status\|who\|wifi}` | CLI tool for gateway uptime, optical power metrics, CPU/RAM utilization, and connected client discovery. |

---

## 📚 Technical Documentation

Detailed guides and protocol breakdowns are organized in [`docs/`](file:///home/broken/myWorld/f670l-toolkit/docs/):

* **[Root Access Technical Analysis](file:///home/broken/myWorld/f670l-toolkit/docs/root_access.md)**: Deep breakdown of the `/webFac` challenge, modular arithmetic solver (`rss.py`), and AES key derivation.
* **[Router Hardening & Debloating Guide](file:///home/broken/myWorld/f670l-toolkit/docs/router_hardening.md)**: Fix IPv6 DNS leaks (Pi-hole), block carrier firmware updates, neutralize 3 AM reboots, and free 16 MB RAM.
* **[VoIP SIP Configuration Guide](file:///home/broken/myWorld/f670l-toolkit/docs/voip_sip.md)**: Airtel Voice VLAN 660 network topology, codec requirements, and softphone client setup.
* **[GPON Optical Identity Cloning](file:///home/broken/myWorld/f670l-toolkit/docs/gpon_cloning.md)**: ONT replacement and provisioning parameters for third-party SFP optical sticks.
* **[Database Command Reference (`sendcmd 1 DB`)](file:///home/broken/myWorld/f670l-toolkit/docs/sendcmd_reference.md)**: Internal NVRAM configuration tables, parameter mapping, and manual modification commands.

---

## ⚠️ Important Invariants

1. **Persistent Flash Save**: Modifications made via `sendcmd 1 DB set ...` reside only in volatile RAM. Always execute `sendcmd 1 DB save` to persist changes across reboots.
2. **Subnet Requirement**: Host PC must be directly connected via LAN 1–3 or Wi-Fi with an IP in `192.168.1.0/24`.
3. **TR-069 Awareness**: To prevent ISP ACS servers from overwriting custom bridge mode or DNS configurations, set `MgtServer.UpgradesManaged = 0` or disable TR-069 (see [Hardening Guide](file:///home/broken/myWorld/f670l-toolkit/docs/router_hardening.md)).

---

## ⚖️ Legal & Safety Disclaimer

> [!WARNING]
> * **Authorized Personal Use**: This toolkit is strictly for diagnostics, research, and personal equipment administration on hardware you own or are authorized to manage (compliant with CFAA, Indian IT Act 2000, and statutory interoperability exemptions).
> * **Optical Laser Safety**: Fiber connections use Class 1 invisible infrared lasers (1310/1490 nm). Never look directly into optical ports or fiber cores.
> * **No Warranty**: Provided "AS IS" under the MIT License. The authors bear no responsibility for ISP terms of service violations, service disruption, or hardware misconfiguration.
