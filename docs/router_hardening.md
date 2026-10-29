# ZTE ZXHN F670L Hardening, Debloating & Performance Tuning Guide

Target Hardware: **ZTE ZXHN F670L GPON Gateway (Airtel Xstream Fiber / Generic FTTH)**  
Firmware: **V9.0.10P18N3D and V9.0 variants**

---

> [!NOTE]
> All changes applied via `sendcmd 1 DB set ...` operate on in-memory configuration tables. To make changes persistent across reboots, you **must** execute:
> ```bash
> sendcmd 1 DB save
> ```

---

## 1. Eliminate IPv6 DNS Leaks (Pi-hole / AdGuard Home)

### The Problem
By default, Airtel's firmware injects carrier IPv6 DNS addresses (`2401:4900:...`) directly into local Router Advertisements (SLAAC / RDNSS) and DHCPv6 pools. Even if your router's IPv4 DNS points to a Pi-hole or AdGuard Home, modern operating systems (iOS, Android, Windows, macOS) prefer IPv6 DNS by default, bypassing your ad-blocker completely.

### The Fix
Inside the root BusyBox shell (`/ # `):

```bash
# 1. Decouple WAN IPv6 DNS from local Router Advertisements (RDNSS):
sendcmd 1 DB set LANDNSOriginCfg 0 v6DnsOrigin 0

# 2. Enable manual DNS assignment in the DHCPv6 stateful server:
sendcmd 1 DB set DHCP6SPool 0 ManualDNSEnable 1

# 3. Set your local Pi-hole / custom DNS IPv6 addresses:
sendcmd 1 DB set DHCP6SPool 0 DNSAddr1 [Your-Primary-Pihole-IPv6]
sendcmd 1 DB set DHCP6SPool 0 DNSAddr2 [Your-Secondary-Pihole-IPv6]

# 4. Point the gateway's internal resolver proxy to your Pi-holes:
sendcmd 1 DB set DNSSettings 0 SerIPv6Address1 [Your-Primary-Pihole-IPv6]
sendcmd 1 DB set DNSSettings 0 SerIPv6Address2 [Your-Secondary-Pihole-IPv6]

# 5. Commit to persistent flash:
sendcmd 1 DB save
```

---

## 2. Block Carrier Firmware Pushes & ACS Overwrites (TR-069 Armor)

### The Problem
ISP Auto-Configuration Servers (ACS) periodically contact the router via TR-069 / CWMP to push unsolicited firmware updates, overwrite custom DNS settings, or reset bridge mode configurations.

### The Fix: Option A (Stealth Mode — Recommended)
Keeps TR-069 periodic inform active so the ISP Network Operations Center (NOC) sees the device as "Online and Healthy", but strictly forbids remote firmware upgrades:

```bash
# Lock firmware upgrade management:
sendcmd 1 DB set MgtServer 0 UpgradesManaged 0

# Commit changes:
sendcmd 1 DB save
```

### The Fix: Option B (Total Severance)
Completely shuts off the TR-069 client daemon:

```bash
sendcmd 1 DB set Tr069Cfg 0 Enable 0
sendcmd 1 DB save
```

---

## 3. Neutralize Scheduled Midnight Reboots (Systematic Reboot)

### The Problem
Airtel firmware includes an analytics script (`systematic_reboot_collect`) that forces an automated gateway reboot at 03:00 AM without user consent, dropping active downloads or long-running tasks.

### The Fix
The reboot schedule is controlled by the persistent `/userconfig/embedur/` configuration:

```bash
# Disable systematic automated reboot:
mkdir -p /userconfig/embedur
echo "sr_disabled = 1" >> /userconfig/embedur/erm_config.ini

# Prevent execution of reboot scripts:
echo "exit 0" > /userconfig/embedur/erm_config_override
chmod +x /userconfig/embedur/erm_config_override
```

---

## 4. Carrier Telemetry Debloat & CPU/RAM Optimization

### The Problem
A background analytics suite (`rrm_zte_mtk`, `climon`, `hmon.exe`, `mosquitto`) continuously runs `top -d 10` loops, collects telemetry, and maintains an open MQTT socket to external carrier servers. This consumes ~16 MB of physical RAM, produces kernel log spam, and increases board temperatures.

### The Fix
1. **Disable Embedur Telemetry Suite**:
   Create a persistent override script on the JFFS2 flash partition:
   ```bash
   echo "exit 0" > /userconfig/embedur/erm_config_override
   chmod +x /userconfig/embedur/erm_config_override
   killall -9 rrm_zte_mtk climon hmon.exe mosquitto 2>/dev/null
   ```

2. **Disable Unnecessary EasyMesh / MultiAP Beacons (If No Extenders Used)**:
   If you do not use secondary mesh extender nodes, stop the background `multiapd` multicast discovery engine:
   ```bash
   sendcmd 1 DB set MultiAPCfg 0 Enable 0
   sendcmd 1 DB set MultiAPCfg 0 SyncEnable 0
   sendcmd 1 DB set MultiAPCfg 0 EnAgentSteer 0
   sendcmd 1 DB set MultiAPMaster 0 EnBandSteer 0
   sendcmd 1 DB set MultiAPMaster 0 EnActiveDeauth 0
   sendcmd 1 DB save
   ```

3. **Silence Verbose Kernel Logging (Printk)**:
   Reduce kernel printk verbosity from Debug Level 7 to Warning Level 4:
   ```bash
   echo "4 4 1 7" > /proc/sys/kernel/printk
   ```

**Measured Result**:
* **Reclaimed RAM**: ~16 MB physical memory restored to the OS pool.
* **Operating Temperature**: Dropped by 2–3 °C (typically from ~51 °C to ~47 °C).
* **Console Noise**: Zero continuous syslog/dmesg spamming.

---

## 5. Network Stack & Buffer Optimization (`sysctl`)

For gigabit fiber connections, tune kernel network buffers to eliminate TCP window throttling over high-bandwidth links:

```bash
# Scale maximum TCP receive buffer to 1 MB (default: 176 KB):
echo 1048576 > /proc/sys/net/core/rmem_max

# Increase ingress network device backlog queue:
echo 2500 > /proc/sys/net/core/netdev_max_backlog

# Prune dead TCP connection tracking states faster (1 hour instead of 2+ hours):
echo 3600 > /proc/sys/net/netfilter/nf_conntrack_tcp_timeout_established

# Ensure IPv4 forwarding is strictly enabled:
echo 1 > /proc/sys/net/ipv4/ip_forward
```

---

## 6. Flash Memory Wear Protection

The internal Telnet daemon (`zxtds`) persistently appends every session login and command to `/userconfig/TdTraceLog.txt` on raw SPI NAND flash (`/dev/mtdblock5`). To prevent premature flash degradation from excessive automated scripts:

```bash
# Check size of trace log:
ls -lh /userconfig/TdTraceLog.txt

# Truncate if growing large:
echo -n > /userconfig/TdTraceLog.txt
chmod 666 /userconfig/TdTraceLog.txt
```
