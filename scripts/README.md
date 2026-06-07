# 📜 Lab Automation & Management Scripts

This directory contains the custom-built logic that powers the automation, security monitoring, and hardware integration of the HomeLab.

## 🛡️ Security & Monitoring
*   **`watch_scanners.sh`**: A real-time log monitor for the Nginx Honeypot. It utilizes `tail` and `grep` to detect unauthorized directory traversal attempts and triggers a push notification to my mobile device via **ntfy.sh**.
*   **`check_ports.sh`**: A utility script to audit the host's network state. It identifies currently occupied ports and suggests available ranges for new Docker deployments, preventing service collisions.

## 🤖 System Automation
*   **`backup_lab.sh`**: The central data integrity script. Triggered nightly via Cron, it performs:
    *   Atomic snapshots of the Vaultwarden SQLite database.
    *   Full dumps of the bare-metal PostgreSQL instance.
    *   Recursive `rsync` of Docker Compose blueprints and project files to external 512GB storage.
    *   7-day retention policy management.
*   **`wake_blaszak.sh`**: Implements Wake-on-LAN logic to remotely power on the main workstation via Magic Packets, including a ping-loop to verify the handshake.

## 📟 Hardware Integration (IoT)
*   **`mqtt_broadcaster.py`**: A Python daemon that gathers system metrics (Time, Load, Alerts) and publishes them to an MQTT broker. This data is consumed by the **Raspberry Pi Pico 2 W** satellite node.
*   **`timer.sh`**: A wrapper that sends specific JSON payloads to the MQTT broker to trigger a physical countdown and alarm sequence on the Pico 2 W dashboard.