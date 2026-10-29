# VoIP / SIP Configuration & Softphone Setup Guide

Target: **ZTE ZXHN F670L GPON Gateway (Airtel Xstream Fiber)**

---

## 1. Architecture: Isolated Voice VLAN

Airtel routes landline telephony over an isolated GPON VLAN:

* **Internet WAN**: VLAN `100` (PPPoE interface `ppp0`) $\rightarrow$ Public Internet / CGNAT
* **Voice WAN**: VLAN `660` (IPoE/DHCP interface `nbif2`) $\rightarrow$ Airtel IMS Core (`ims.airtel.in`)

Because VLAN 660 is strictly isolated from the local LAN bridge (`br0`), SIP softphones running on local Wi-Fi/Ethernet cannot route directly to the IMS Session Border Controller without routing rules or proxying through the gateway.

---

## 2. SIP Parameter Reference

Extract your account details using `./scripts/extract_credentials.py`. The parameters map as follows:

| Parameter | Example Value / Template | Notes |
| :--- | :--- | :--- |
| **User ID / Account** | `+9140XXXXXXXX` | 10-digit number with country code |
| **Authentication ID** | `+9140XXXXXXXX@ims.airtel.in` | Digest authentication username |
| **Authentication Password**| *(Extracted from `VoIPSIPLine`)* | MD5 digest password |
| **Domain / Realm** | `ims.airtel.in` | Airtel national IMS domain |
| **Outbound Proxy** | `10.232.xxx.xxx:5060` | Regional IMS SBC IP (UDP) |
| **Transport** | **UDP** | Port 5060 |
| **Supported Codecs** | **G.711A (PCMA)**, G.711U (PCMU), G.729, G.722 | 20 ms packetization (`ptime=20`) |

---

## 3. Client Softphone Configuration (Zoiper / Grandstream Wave)

1. **Account Name**: `Airtel Landline`
2. **User ID / SIP Username**: `+9140XXXXXXXX`
3. **Authentication Username**: `+9140XXXXXXXX@ims.airtel.in`
4. **Password**: `<your_sip_password>`
5. **Domain**: `ims.airtel.in`
6. **Outbound Proxy**: `<your_outbound_proxy_ip>:5060`
7. **Network Transport**: `UDP`
