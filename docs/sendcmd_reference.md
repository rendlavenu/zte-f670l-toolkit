# ZTE sendcmd Database Manipulation Reference

In the ZTE BusyBox root shell (`/ # `), the `sendcmd 1 DB` binary utility provides direct low-level read and write access to all persistent configuration tables stored in the gateway NVRAM/flash memory.

---

> [!CAUTION]
> **NVRAM Integrity & Write Endurance Hazard**:
> Direct manipulation of internal database tables bypasses standard web GUI input validation.
> * **Bootloop Risk**: Setting malformed configuration parameters or invalid network masks can cause runtime daemon crashes (`httpd`, `cspd`, `omcid`) resulting in cyclic reboot loops ("soft bricks").
> * **Flash Endurance**: The gateway uses NAND/SPI flash memory with finite write cycles. Avoid executing automated write loops or excessive `sendcmd 1 DB save` invocations to prevent premature flash memory degradation.

---

## 1. Syntax Overview

```bash
# Print entire table contents:
sendcmd 1 DB p [Table]

# Query a specific row and parameter:
sendcmd 1 DB get [Table] [RowNo] [Parameter]

# Modify a parameter value in RAM cache:
sendcmd 1 DB set [Table] [RowNo] [Parameter] [Value]

# Persist all modified tables from RAM to flash (MANDATORY):
sendcmd 1 DB save

# Enumerate all available database tables:
sendcmd 1 DB all
```

---

## 2. Core Configuration Tables Reference

| Table Name | Description | Key Parameters |
| :--- | :--- | :--- |
| **`PPPIF`** | PPPoE WAN Authentication | `Username`, `Password`, `ServiceName`, `ConnType`, `MTU` |
| **`VoIPSIPLine`** | Voice SIP Account Credentials | `DirectoryNumber`, `AuthUserName`, `AuthPassword` |
| **`VoIPSIPServer`** | Voice SIP Server Topology | `RegistrarServer`, `OutBoundProxy`, `DomainName`, `ProxyPort` |
| **`GPON`** | Optical Physical Identifiers | `GponSN`, `Passwd` (SLID/PLOAM), `LOID`, `LOIDPasswd` |
| **`WLANBase`** | Wi-Fi Radios & SSIDs | `ESSID`, `WpaPsk`, `BeaconType`, `Channel`, `HideSSID` |
| **`PortControl`** | LAN/WAN Physical Port Matrix | Port binding masks used for WAN Bridge Mode allocation |
| **`WANCPPP`** | WAN Connection Mode | `WANCType` (`0` = Routing mode, `1` = Bridge mode) |
| **`DevInfo`** | Hardware & Firmware Identity | `ModelName`, `SoftwareVer`, `HardwareVer`, `SerialNumber` |
| **`TelnetCfg`** | Telnet Daemon Configuration | `TelnetEnable` (`1` = Active, `0` = Disabled), `TS_Port` (`23`) |
| **`Tr069Cfg`** | ISP Remote Management (CWMP) | `ServerURL`, `Username`, `Password`, `Enable` (`0` = Disable ACS) |

---

## 3. Safe Execution Protocol

1. **Read Before Writing**: Always execute `sendcmd 1 DB p [Table]` before issuing any `set` command to verify table index and current field values.
2. **Explicit Persistence**: Modifications applied via `sendcmd 1 DB set` reside only in volatile RAM. They are completely discarded on reboot unless followed by:
   ```bash
   sendcmd 1 DB save
   ```
3. **Rollback Precaution**: Maintain a written record or copy of original parameters before modifying optical (`GPON`), WAN (`PPPIF`, `WANCPPP`), or management (`Tr069Cfg`) tables.
