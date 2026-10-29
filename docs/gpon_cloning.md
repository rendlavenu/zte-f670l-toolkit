# GPON Optical Cloning & ONT Replacement Guide

Target: **ZTE ZXHN F670L GPON Gateway (ITU-T G.984.3)**

---

## 1. Parameters Required for Upstream OLT Authorization

To replace the ISP gateway with a third-party GPON ONT, SFP stick (e.g. DFP-34X-2C2, CarlitoxxPro, Huawei MA5671A, VSOL, XPON), extract the following values via `./scripts/extract_credentials.py`:

| Parameter | Format / Example | Target Configuration on SFP Stick / ONT |
| :--- | :--- | :--- |
| **Vendor ID** | `ZTEG` | GPON Vendor ID (Hex: `5A 54 45 47`) |
| **GPON Serial (ASCII)** | `ZTEGxxxxxxxx` | 12-character alphanumeric serial |
| **GPON Serial (HEX)** | `5A544547xxxxxxxx` | 16-character hexadecimal serial |
| **SLID / PLOAM Password** | `Gxxxxxxxx` (or blank) | Physical Layer OAM Password |
| **LOID / LOID Pass** | `123456789` / `123456` | Logical ONT ID (Airtel default profiles) |
| **Base MAC Address** | `AA:BB:CC:DD:EE:FF` | Cloned MAC address on upstream interface |
| **OMCI Equipment ID** | `F670LV9.0` | Reported via OMCI Managed Entity 257 |

---

## 2. Provisioning Steps on Third-Party ONT

1. Set the ONT Mode to **GPON** (Class B+ / C+).
2. Set **Vendor ID** to `ZTEG`.
3. Set **GPON Serial Number** (ASCII or Hex matching the table above).
4. Clone the **Base MAC Address** to the ONT WAN/Host interface.
5. Set VLAN `100` on the Ethernet interface for Internet (PPPoE).
6. Set VLAN `660` on a separate interface if routing VoIP SIP traffic.
7. Connect the SC/APC fiber patch cable. Verify that the OLT status transitions to **O5 (Operation state)**.
