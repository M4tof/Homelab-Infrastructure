# Secure Edge Homelab (RPi5)

A comprehensive personal infrastructure project focusing on **DevOps, Security, and Embedded Systems integration.** This repository documents the architecture, automation scripts, and orchestration of my home-based server environment.

## 🛠 Tech Stack
- **Compute:** Raspberry Pi 5 (4GB) | Debian Bookworm
- **Storage:** 128GB NVMe SSD (PCIe Gen 3) | 512GB USB Backup
- **Orchestration:** Docker & Dockge
- **Networking:** Tailscale (Zero Trust VPN), UFW (Uncomplicated Firewall)
- **Monitoring:** Zabbix, Grafana, Netdata, Scrutiny
- **Database:** PostgreSQL (Bare-metal for performance)

## 🔐 Security Architecture (Cybersecurity Focus)
As a student pursuing a Master's in Cybersecurity, this lab serves as a testing ground for hardening and monitoring:
- **The Honeypot ("The Trap"):** An Nginx decoy landing page on Port 80. Accessing `/admin/` triggers an immediate `ntfy` alert to my mobile device via a custom watcher service.
- **Access Control:** No open ports on the public internet. Remote access is strictly managed via **Tailscale VPN**.
- **Hardening:** Current Lynis Hardening Index of **71**. Implemented `Fail2Ban` for SSH and `ClamAV` for malware detection.
- **Audit Automation:** Custom `lab-audit` alias triggers automated Lynis scans and security reporting.

## 🤖 Automation & Monitoring
I consider myself an "Engineer first, Programmer second." If a task is repeatable, it is automated:
- **Custom CLI Tooling:** Developed a suite of bash aliases for system health, backup management, and automated security patching.
- **Proactive Monitoring:** Hardware health is tracked via Netdata with a thermal ceiling alert set at 70°C, since in manual tests the temperature has yet to climb over 66°C
- **Data Integrity:** Daily automated backups to an external encrypted drive with S.M.A.R.T. monitoring via Scrutiny.

## 📟 Hardware Integration
- **Micro-Controller Interface:** Integrated a **Raspberry Pi Pico 2 W** acting as a physical telemetry dashboard (LCD & 7-Segment display) communicating via MQTT.
- **Device Management:** CUPS controll for legacy HP printer.

## 📁 Repository Structure
- `/docker`: Docker Compose blueprints for the service stack.
- `/scripts`: Bash scripts for backups, honeypot monitoring, and system management.
- `/docs`: Detailed system documentation and hardware diagrams.
