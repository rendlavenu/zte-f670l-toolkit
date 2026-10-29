# AI Assistant Guide & Repository Instructions

This document provides architectural context, hardware invariants, and safety guidelines for AI assistants (Antigravity, Claude Code, Cursor, Copilot) working on this repository.

---

## 1. Target Hardware & Environment

* **Target Hardware**: ZTE ZXHN F670L GPON Gateway (Hardware Version V9.0)
* **SoC Architecture**: Sanechips / ZTE ZX279128S (Dual-Core ARMv7 Cortex-A9, Linux 4.1.25)
* **Target Firmware**: `V9.0.10P18N3D` (Build date: June 27, 2025) and compatible V9.0 releases
* **Target ISP Context**: Bharti Airtel (Airtel Xstream Fiber) and generic GPON FTTH deployments
* **Root Shell Environment**: BusyBox v1.17.2 ash prompt (`/ # `) via TCP port 23

---

## 2. Invariants & Domain Rules (Never Violate)

1. **Commit All Changes (`sendcmd 1 DB save`)**:
   - Any database modification using `sendcmd 1 DB set [Table] [Row] [Field] [Val]` modifies only the in-memory RAM copy of the database.
   - Changes are **lost on reboot** unless explicitly persisted using `sendcmd 1 DB save`.
   - Always verify and remind users to commit changes.

2. **Zero Hardcoded Personal Identifiers**:
   - Never commit or print real personal PPPoE credentials, VoIP SIP passwords, live MAC addresses, or real GPON serial numbers.
   - In all documentation and code examples, use sanitized placeholders (`+9140XXXXXXXX`, `ZTEGxxxxxxxx`, `10.232.xxx.xxx`).

3. **Dynamic Network Routing Detection**:
   - Do not hardcode client network interface names (e.g., `eth0` or `wlan0`).
   - Use dynamic routing queries (`ip route get <target>`) to resolve the active interface and its corresponding MAC address.

4. **Preserve TR-069 Awareness**:
   - When users configure custom Bridge Mode or DNS settings, be aware that ISP ACS servers may query the router via TR-069 and overwrite parameters.
   - Suggest disabling periodic inform via `sendcmd 1 DB set Tr069Cfg 0 Enable 0` if persistent custom configurations are required.

5. **Safety & Regulatory Compliance**:
   - Always include standard optical laser safety warnings when discussing fiber or SFP ONT replacement.
   - Maintain the standard legal disclaimer regarding authorized personal use, ISP Subscriber Agreements, and emergency telephony services.

---

## 3. Toolset & Architecture

```text
f670l-toolkit/
├── README.md                  # Main guide & documentation
├── AGENT.md                   # AI Assistant instructions (this file)
├── CLAUDE.md                  # Symlink to AGENT.md
├── requirements.txt           # Python dependencies (requests, pycryptodome)
├── lib/
│   ├── zte_unlock.py          # /webFac cryptographic handshake engine
│   └── rss.py                 # Modular exponentiation solver (do_check_client)
├── scripts/
│   ├── router_shell.py        # Interactive root BusyBox shell
│   ├── extract_credentials.py # Automated credential extraction tool
│   ├── router_ctl.py          # Command-line status, telemetry & client discovery
│   └── enable_bridge.py       # WAN bridge mode configurator
└── docs/
    ├── root_access.md         # /webFac protocol & cryptographic analysis
    ├── voip_sip.md            # VoIP configuration & softphone client setup
    ├── gpon_cloning.md        # GPON ONT replacement & SFP stick guide
    └── sendcmd_reference.md   # Internal database manipulation reference
```

---

## 4. Verification & Testing Commands

```bash
# Verify Python script syntax
python3 -m py_compile lib/zte_unlock.py lib/rss.py scripts/*.py

# Test root shell connectivity
./scripts/router_shell.py --host 192.168.1.1

# Test credential extraction
./scripts/extract_credentials.py --host 192.168.1.1

# Query router telemetry
./scripts/router_ctl.py status
```
