# ZTE sendcmd Database Manipulation Reference

In the ZTE BusyBox root shell (`/ # `), the `sendcmd 1 DB` utility provides direct read and write access to all persistent configuration tables stored in flash memory.

---

## 1. Syntax Overview

```bash
# Print entire table:
sendcmd 1 DB p [Table]

# Set a parameter value:
sendcmd 1 DB set [Table] [RowNo] [Parameter] [Value]

# Commit changes to persistent flash (MANDATORY):
sendcmd 1 DB save

# List all tables:
sendcmd 1 DB all
```

---

## 2. Key Database Tables

| Table | Purpose | Common Parameters |
| :--- | :--- | :--- |
| **`PPPIF`** | PPPoE Authentication | `Username`, `Password`, `ServiceName`, `ConnType` |
| **`VoIPSIPLine`** | SIP Account | `DirectoryNumber`, `AuthUserName`, `AuthPassword` |
| **`VoIPSIPServer`** | SIP Gateways | `RegistrarServer`, `OutBoundProxy`, `DomainName` |
| **`GPON`** | Optical Identifiers | `GponSN`, `Passwd`, `LOID`, `LOIDPasswd` |
| **`WLANBase`** | Wi-Fi Radios & SSIDs | `ESSID`, `WpaPsk`, `BeaconType`, `Channel` |
| **`PortControl`** | LAN/WAN Port Binding | Port mapping matrix for Bridge Mode |
| **`WANCPPP`** | WAN PPP Settings | `WANCType` (0 = Route, 1 = Bridge) |
| **`DevInfo`** | Hardware Identity | `ModelName`, `SoftwareVer`, `SerialNumber` |
| **`TelnetCfg`** | Telnet Daemon | `TelnetEnable`, `TS_Port` |
| **`Tr069Cfg`** | TR-069 ACS Settings | `ServerURL`, `Username`, `Password`, `Enable` |
