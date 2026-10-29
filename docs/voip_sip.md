# VoIP / SIP Configuration & Softphone Setup Guide

**Target Gateway**: ZTE ZXHN F670L GPON Gateway (Bharti Airtel / Generic FTTH)  
**Protocol Standards**: Session Initiation Protocol (RFC 3261), ITU-T G.711A (PCMA), SDP (RFC 4566)

---

> [!WARNING]
> **Emergency Services Notice (112 / 911 / E911)**:
> Extracted SIP credentials routed through third-party softphones or PBX servers must **NOT** be relied upon as the primary means of reaching emergency service dispatchers. ISP emergency routing depends on specific physical line identification and local gateway provisioning. Always maintain an alternative communications method for emergency dispatch.

---

## 1. Network Topology: Voice VLAN Isolation

Airtel Xstream Fiber segregates broadband Internet traffic and Voice over IP (VoIP) at the optical layer using 802.1Q Virtual Local Area Networks (VLANs):

* **Internet WAN**: VLAN `100` (PPPoE interface `ppp0`) $\rightarrow$ Routes to public Internet / CGNAT.
* **Voice WAN**: VLAN `660` (IPoE / DHCP interface `nbif2`) $\rightarrow$ Routes strictly to Airtel IMS Core (`ims.airtel.in`).

```
                    ┌──────────────────────────┐
                    │     Airtel OLT / PON     │
                    └────────────┬─────────────┘
                                 │ Fiber (ITU-T G.984)
                    ┌────────────┴─────────────┐
                    │ ZTE ZXHN F670L Gateway   │
                    └───┬──────────────────┬───┘
     VLAN 100 (Internet)│                  │VLAN 660 (IMS Voice)
     ┌──────────────────┴──┐            ┌──┴──────────────────┐
     │  Local LAN / Wi-Fi  │            │ Internal SIP Stack  │
     │  (192.168.1.0/24)   │            │ (10.232.xxx.xxx)    │
     └─────────────────────┘            └──────────┬──────────┘
                                                   │ FXS Port (RJ-11)
                                        ┌──────────┴──────────┐
                                        │ Analog Landline Tel │
                                        └─────────────────────┘
```

Because VLAN 660 is completely isolated from the standard LAN bridge (`br0`), softphones connected to local Wi-Fi or Ethernet cannot communicate directly with the IMS Session Border Controller (SBC) without custom static routes or dual-WAN routing.

---

## 2. SIP Parameter Mapping Reference

Run [`scripts/extract_credentials.py`](../scripts/extract_credentials.py) to read provisioned parameters directly from NVRAM (`VoIPSIPLine` and `VoIPSIPServer` tables):

| SIP Parameter | Configuration Value / Format | Description |
| :--- | :--- | :--- |
| **SIP User ID / Display Name** | `+9140XXXXXXXX` | E.164 formatted telephone number (including country code) |
| **Authentication Username** | `+9140XXXXXXXX@ims.airtel.in` | Digest authentication user identity |
| **Authentication Password** | `<extracted_md5_password>` | SIP MD5 digest authentication token |
| **SIP Domain / Realm** | `ims.airtel.in` | National IMS FQDN domain |
| **Outbound Proxy** | `10.232.xxx.xxx:5060` | Regional IMS Session Border Controller IP (UDP) |
| **Transport Protocol** | **UDP** | Standard SIP signaling on port 5060 |
| **Supported Audio Codecs** | **G.711A (PCMA)**, G.711U, G.729 | 20 ms packetization (`ptime=20`) |

---

## 3. Client Softphone Configuration Profile (Zoiper / Grandstream Wave)

To configure a client device (when connected to a routed voice network or gateway VPN):

1. **Account Name**: `Airtel Landline`
2. **User ID / SIP Username**: `+9140XXXXXXXX`
3. **Authentication Username**: `+9140XXXXXXXX@ims.airtel.in`
4. **Password**: `<extracted_md5_password>`
5. **Domain / Realm**: `ims.airtel.in`
6. **Outbound Proxy**: `<regional_sbc_ip>:5060`
7. **Network Transport**: `UDP`
8. **Audio Codec Priority**: Force `G.711 A-law (PCMA)` to match carrier transcoding.
