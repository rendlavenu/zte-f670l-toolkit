# ZTE ZXHN F670L Root Access Technical Analysis

Target: **ZTE ZXHN F670L GPON Gateway (Hardware V9.0, Firmware V9.0.10P18N3D and V9.0 variants)**

---

## 1. Vulnerability Architecture: The `/webFac` Interface

ZTE gateway firmware includes a hidden factory diagnostic endpoint at `/webFac` and `/webFacEntry`. These endpoints allow authorized manufacturing test equipment to elevate privileges and start a temporary root Telnet session on TCP port 23.

### Authentication Protocol Flow

```
Client (PC)                                               ZTE F670L Gateway
    │                                                              │
    ├── 1. POST /webFac (SendSq.gch) ─────────────────────────────>│ (Reset state)
    │<── HTTP 400 (Expected reset confirmation) ───────────────────┤
    │                                                              │
    ├── 2. POST /webFac (RequestFactoryMode.gch) ─────────────────>│ (Trigger challenge)
    │                                                              │
    ├── 3. POST /webFac (SendSq.gch?rand=0) ───────────────────────>│
    │<── HTTP 200 "re_rand=server_rand&seed&server_mac" ───────────┤
    │                                                              │
    │    [Compute Modular Exponentiation using client & server MAC]│
    │    [Derive 24-byte AES-ECB Key from KEY_POOL offset by seed] │
    │                                                              │
    ├── 4. POST /webFacEntry (SendInfo.gch?info=...) [AES encrypted]>│
    │<── HTTP 200 ─────────────────────────────────────────────────┤
    │                                                              │
    ├── 5. POST /webFacEntry (CheckLoginAuth.gch)   [AES encrypted]>│ (Validate web user/pass)
    │<── HTTP 200 (FactoryMode.gch session token) ─────────────────┤
    │                                                              │
    ├── 6. POST /webFacEntry (FactoryMode.gch?mode=2)[AES encrypted]>│ (Elevate privilege)
    │<── HTTP 200 "FactoryModeAuth.gch?user=<user>&pass=<pass>" ───┤
    │                                                              │
    ├── 7. Telnet Connect to Port 23 ─────────────────────────────>│
    │    (Authenticate with session user/pass)                    │
    │<── Root BusyBox Ash Prompt ("/ # ") ─────────────────────────┤
```

---

## 2. Cryptographic Handshake Details

### A. Modular Exponentiation Solver (`rss.py`)
In `httpd`, the function `do_check_client` validates that the client data block matches the client MAC and server MAC:
$$\text{work\_buffer}[i] = (\text{client\_data}[i])^e \pmod m$$
Where the exponent $e$ and modulus $m$ are derived from word transformations using polynomial $x^{0x1687} \pmod{0x7561}$.

### B. AES-128-ECB Key Derivation
The key is derived from an 88-byte firmware key pool (`KEY_POOL`):
$$\text{index} = (\text{client\_xor\_server}) \pmod{60}$$
$$\text{key}[i] = \text{KEY\_POOL}[\text{index} + i] \oplus \text{0xA5}$$

---

## 3. Session Lifespan & Security Invariants
- The generated Telnet session user (e.g., `9nU5kSEx`) is temporary and valid for the current factory session.
- Once factory mode is elevated, TCP port 23 remains open until the router reboots or factory mode is closed.
- All configuration changes made via `sendcmd 1 DB set ...` must be explicitly committed to flash using `sendcmd 1 DB save`.
