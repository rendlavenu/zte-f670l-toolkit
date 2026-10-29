# ZTE ZXHN F670L Root & Management Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Target Hardware](https://img.shields.io/badge/Target-ZTE%20ZXHN%20F670L%20V9.0-blue.svg)](#)
[![Tested Firmware](https://img.shields.io/badge/Firmware-V9.0.10P18N3D-brightgreen.svg)](#)

A target-focused reverse-engineering and automation toolkit for the **ZTE ZXHN F670L GPON Gateway** (Hardware V9.0, running firmware `V9.0.10P18N3D` and V9.0 variants, commonly deployed on Airtel Xstream Fiber).

Provides tools to spawn a root BusyBox shell via the factory diagnostic interface, extract locked credentials (PPPoE, VoIP SIP, GPON SN), and configure true Bridge Mode for third-party routers.

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
git clone https://github.com/rendlavenu/f670l-toolkit.git
cd f670l-toolkit
pip install -r requirements.txt
```

### 2. Spawn an Interactive Root Shell
```bash
./scripts/router_shell.py
```
*(Prompts for router web credentials, solves the cryptographic factory handshake, and opens a root BusyBox ash shell: `/ # `).*

### 3. Extract All Credentials (PPPoE, VoIP SIP, GPON SN, Wi-Fi)
```bash
./scripts/extract_credentials.py
```
*(Prints a structured table of PPPoE internet credentials, VoIP SIP passwords, GPON optical provisioning tokens, and Wi-Fi pre-shared keys. Use `--json` for machine-readable output).*

### 4. Enable WAN Bridge Mode
```bash
./scripts/enable_bridge.py --lan-port 4
```
*(Bridges WAN VLAN 100 directly to LAN4 for third-party routers like pfSense, OPNsense, OpenWrt, or UniFi).*

---

## 📌 Features & Capabilities

| Capability | Tool / Script | Description |
| :--- | :--- | :--- |
| **Interactive Root Shell** | [`scripts/router_shell.py`](file:///home/broken/myWorld/f670l-toolkit/scripts/router_shell.py) | Full terminal access to router OS (Linux 4.1.25 / BusyBox v1.17.2). |
| **Credential Extraction** | [`scripts/extract_credentials.py`](file:///home/broken/myWorld/f670l-toolkit/scripts/extract_credentials.py) | Reads plaintext PPPoE, SIP, GPON SN, and Wi-Fi keys directly from flash memory. |
| **Bridge Mode Setup** | [`scripts/enable_bridge.py`](file:///home/broken/myWorld/f670l-toolkit/scripts/enable_bridge.py) | Binds physical LAN ports to WAN VLAN 100 for external router PPPoE dialing. |
| **Cryptographic Engine** | [`lib/zte_unlock.py`](file:///home/broken/myWorld/f670l-toolkit/lib/zte_unlock.py) | Implements modular arithmetic solver and AES key derivation for `/webFac`. |

---

## 🛠 Manual Database Reference (`sendcmd 1 DB`)

Once inside the root shell (`/ # `), use `sendcmd 1 DB` to inspect or modify router settings directly:

```bash
# Print tables:
sendcmd 1 DB p PPPIF          # PPPoE credentials
sendcmd 1 DB p VoIPSIPLine     # SIP username & password
sendcmd 1 DB p VoIPSIPServer   # SIP Registrar & Outbound Proxy
sendcmd 1 DB p GPON            # GPON Serial Number & PLOAM password
sendcmd 1 DB p WLANBase        # Wi-Fi SSIDs & WPA pre-shared keys
sendcmd 1 DB p PortControl     # Physical port mapping matrix
sendcmd 1 DB p DevInfo         # Hardware & firmware identity

# Commit changes to persistent flash (MANDATORY after set):
sendcmd 1 DB save
```

---

## 🔍 Critical Edge Cases & Troubleshooting

### 1. Connection Timeout or Connection Refused
* **Cause**: Client PC is not on the same subnet as the gateway, or connected via an external router.
* **Fix**: Connect your PC directly to LAN 1–3 or Wi-Fi of the F670L. Ensure your IP is in `192.168.1.x`.

### 2. Handshake Failure on Step 4 (`CheckLoginAuth`)
* **Cause**: Incorrect web admin username or password, or another active web session holding the lock.
* **Fix**: Log out of the web interface in your browser, wait 10 seconds, and rerun `./scripts/router_shell.py`.

### 3. TR-069 Configuration Overwrite
* **Cause**: ISP ACS servers periodically query the router and re-apply default configuration profiles.
* **Fix**: To prevent TR-069 from reverting custom settings, disable the TR-069 periodic inform client via the root shell:
  ```bash
  sendcmd 1 DB set Tr069Cfg 0 Enable 0
  sendcmd 1 DB save
  ```

---

## 📁 Repository Structure

```text
f670l-toolkit/
├── README.md                  # Technical guide & quick start
├── LICENSE                    # MIT License
├── requirements.txt           # Python dependencies (requests, pycryptodome)
├── AGENT.md                   # AI Assistant instructions
├── CLAUDE.md                  # Symlink to AGENT.md
├── lib/
│   ├── zte_unlock.py          # /webFac cryptographic handshake engine
│   └── rss.py                 # Modular exponentiation solver (do_check_client)
├── scripts/
│   ├── router_shell.py        # Interactive root BusyBox shell
│   ├── extract_credentials.py # Automated credential extraction tool
│   └── enable_bridge.py       # WAN bridge mode configurator
└── docs/
    ├── root_access.md         # /webFac protocol & cryptographic analysis
    ├── voip_sip.md            # VoIP configuration & softphone client setup
    ├── gpon_cloning.md        # GPON ONT replacement & SFP stick guide
    └── sendcmd_reference.md   # Internal database manipulation reference
```

---

## ⚠️ Disclaimer & Legal Notice

> [!WARNING]
> 1. **Educational & Research Purpose Only**: This toolkit is provided strictly for personal network administration, interoperability testing, and security research under fair-use provisions.
> 2. **No Warranty & Limitation of Liability**: Modifying router configurations carries inherent risks of service disruption or misconfiguration. Provided "AS IS" without warranty of any kind.
> 3. **Trademarks**: All trademarks, brand names, and models (ZTE, ZXHN, Airtel) cited herein belong to their respective owners and are referenced solely for technical identification.
