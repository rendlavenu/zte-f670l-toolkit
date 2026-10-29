# GPON Optical Identity Cloning & Third-Party ONT Migration

**Target Hardware**: ZTE ZXHN F670L GPON Gateway  
**Optical Standards**: ITU-T G.984.1–G.984.4 (GPON), G.988 (OMCI)

---

> [!CAUTION]
> **Optical Laser Radiation Hazard**:
> Fiber optic broadband connections use Class 1 / Class 1M infrared semiconductor lasers operating at nominal wavelengths of 1310 nm (upstream) and 1490 nm (downstream).
> * The emitted laser radiation is **completely invisible** to the naked human eye.
> * **NEVER** look directly into the optical fiber core, optical patch cables, or the transceiver optical bore.
> * Exposure can cause immediate and irreversible retinal burns. Always disconnect optical power or cap optical ports when inspecting hardware.

> [!WARNING]
> **ISP Compliance & Network Integrity Notice**:
> Replacing an ISP-provided Optical Network Terminal (ONT) or cloning optical serial numbers onto third-party transceivers (e.g., SFP/SFP+ ONTs) may breach your ISP Subscriber Agreement and local telecommunications equipment compliance standards (such as TEC/DoT in India, FCC regulations in the US). Misconfigured optical parameters (e.g., rogue ONU continuous laser transmission) can disrupt service for all subscribers on the same optical distribution network (ODN) splitter. Proceed only in isolated lab environments or with authorization.

---

## 1. Parameters Required for Upstream OLT Authorization

GPON Optical Line Terminals (OLTs) validate customer ONTs during Phase O3 (Serial Number acquisition) and Phase O4 (Ranging). To authorize a replacement device (such as an SFP ONT stick: DFP-34X-2C2, CarlitoxxPro, Huawei MA5671A, VSOL, XPON), extract the following parameters using [`scripts/extract_credentials.py`](../scripts/extract_credentials.py):

| Provisioning Parameter | Format / Specification | Example / Value | Notes |
| :--- | :--- | :--- | :--- |
| **Vendor ID** | 4 ASCII Characters | `ZTEG` | Hex: `5A 54 45 47` |
| **GPON Serial (ASCII)** | 12 ASCII Characters | `ZTEGxxxxxxxx` | 4-char vendor prefix + 8-char hex serial |
| **GPON Serial (HEX)** | 16 Hexadecimal Digits | `5A544547xxxxxxxx` | Used directly by Linux `/proc` or `fw_setenv` |
| **SLID / PLOAM Password** | 10 ASCII/Hex Bytes | `Gxxxxxxxx` / Empty | Physical Layer OAM password (if provisioned) |
| **LOID / LOID Password** | Alphanumeric String | `123456789` / `123456` | Logical ONT Identifier used in some OLT profiles |
| **Base MAC Address** | IEEE 802 MAC Address | `AA:BB:CC:DD:EE:FF` | Cloned onto the ONT host/WAN interface |
| **OMCI Equipment ID** | Alphanumeric String | `F670LV9.0` | Reported in OMCI Managed Entity 257 |
| **Hardware Version** | String | `V9.0` | Reported in OMCI ME 257 |
| **Software Version** | String (Active/Standby) | `V9.0.10P18N3D` | Firmware release string matched to carrier profile |

---

## 2. Third-Party ONT Provisioning Checklist

1. **Verify Laser Mode**: Confirm the third-party ONT is set to standard GPON mode (ITU-T G.984 Class B+ or C+ optical budget).
2. **Apply Identity Configuration**:
   * Set `Vendor ID` = `ZTEG`.
   * Set `GPON Serial Number` = extracted ASCII/HEX serial.
   * Set `PLOAM Password` / `SLID` if present in original gateway configuration.
   * Clone the `Base MAC Address` to the ONT management and WAN interfaces.
3. **Configure VLAN Forwarding**:
   * Set WAN VLAN `100` on the Ethernet interface for Internet (PPPoE).
   * Set WAN VLAN `660` on a secondary virtual interface if routing VoIP SIP traffic.
4. **Optical Connection**: Clean the SC/APC fiber ferrule before insertion. Connect the green SC/APC connector to the optical transceiver.
5. **Verify State Machine**: Inspect the ONT optical status. The optical link state must progress:
   $$\text{O1 (Initial)} \rightarrow \text{O2 (Standby)} \rightarrow \text{O3 (Serial Number)} \rightarrow \text{O4 (Ranging)} \rightarrow \text{O5 (Operation)}$$
   State **O5** indicates complete optical synchronization and OMCI provisioning.
