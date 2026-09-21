# 📟 Satellite Telemetry Node (RP2350)

This directory contains the C++ firmware for the **Raspberry Pi Pico 2 W**, acting as the autonomous physical monitoring interface and "Edge Watchdog" for the HomeLab cluster.

## 🧠 Dual-Core Architecture
The project leverages the dual-core RP2350 to ensure high-performance UI and non-blocking network operations:

- **Core 0 (Management & Comms):** Handles WiFi/MQTT connectivity, keeps synchronization with the HomeLab cluster, dispatches `ntfy.sh` push notifications, and manages the **REST API** for configuration.
- **Core 1 (Real-time UI):** Dedicated strictly to the high-frequency multiplexing of the 4-digit 7-segment display to ensure a flicker-free visual output.

## ✨ Core Features
- **Cluster Watchdog:** Monitors the MQTT heartbeat from the HomeLab Master node. Triggers an integrated **RGB LED Warning System** and local alarm if the cluster is unreachable for >120 seconds.
- **Hardware Telemetry:** Monitors ambient light levels via a photoresistor-based feedback loop with hysteresis to control LCD backlight intensity automatically.
- **Remote Configuration:** Exposes a local REST API (`/api/config`) allowing dynamic adjustment of system thresholds (e.g., light sensitivity, backlight modes) without reflashing firmware.
- **Dynamic Messaging:** Supports a custom LCD message format, allowing server-side push notifications to update the physical display remotely.
- **NTP-Sync:** Real-time clock maintenance, periodically "snapping" to the master HomeLab time via NTP-synced MQTT payloads.

## 🛠️ Physical Dashboard Interface
- **16x2 I2C LCD:** Displays system uptime, real-time RAM utilization, and thermal delta (T_current - T_ambient).
- **Multiplexed 7-Segment Display:** Accurate server-time clock.
- **RGB LED Warning System:** Tri-colour system state indicator:
    - 🟢 **Green:** System OK / Live.
    - 🔵 **Blue:** Information / Warning.
    - 🔴 **Red:** Critical / Cluster Heartbeat Lost.
- **Auto-Backlight:** Logic-controlled display brightness preventing light pollution in low-light conditions.

## 🔌 API & Integration
The node provides a lightweight HTTP server for status querying and configuration:
- `GET /api` - Returns system telemetry (uptime, temp, RAM, MQTT status, light level).
- `POST /api/config` - Dynamically update parameters like `backlight_mode` or `LIGHT_THRESHOLD`.