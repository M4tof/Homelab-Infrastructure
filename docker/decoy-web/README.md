# 🪤 The Trap: Nginx HoneyPot

This service acts as a "Digital Tripwire" (Intrusion Detection System) on the local network. It is designed to identify and alert against unauthorized internal scanning or lateral movement.

## 🛡️ Security Concept
- **Port 80 Decoy:** While all actual lab management is hidden on obscure ports or behind the VPN, this Nginx instance occupies standard Port 80 to attract automated scanners.
- **The HoneyPot:** Accessing the root provides a boring "403 Forbidden" page. However, common administrative paths (like `/admin/`) are active "traps."

## 📡 The Alerting Pipeline
This container works in tandem with the **[watch_scanners.sh](../../scripts/watch_scanners.sh)** script located in the `/scripts` directory:

1. **Access:** A scanner hits `http://[pi-ip]/admin/`.
2. **Logging:** Nginx logs the hit to a persistent volume shared with the host SSD.
3. **Detection:** The `decoy-monitor.service` (Systemd) runs a Bash watcher that monitors the logs in real-time.
4. **Notification:** An immediate push notification is sent to my mobile device via **ntfy.sh** including the attacker's IP address.

## 📂 Components
- `html/`: Contains the decoy landing pages.
- `logs/`: Persistent log storage mapped to the host for monitoring.