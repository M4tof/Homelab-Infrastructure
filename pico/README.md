# 📟 Satellite Telemetry Node (RP2350)

This directory contains the C++ firmware for the **Raspberry Pi Pico 2 W** acting as the physical monitoring interface for the HomeLab.

## 🧠 Dual-Core Architecture
The project utilizes the dual-core capabilities of the RP2350:
- **Core 0 (Management):** Handles WiFi connectivity, MQTT subscription to the Pi 5 broker, ntfy.sh alert dispatching, and the I2C 16x2 LCD interface.
- **Core 1 (Real-time):** Dedicated strictly to the high-frequency multiplexing of the 4-digit 7-segment display to ensure a flicker-free UI.

## ✨ Features
- **Self-Correcting Clock:** Keeps time locally using internal oscillators, periodically "snapping" to the Pi 5 NTP-synced time via MQTT.
- **Adaptive Display:** Utilizes a photoresistor-based feedback loop with hysteresis to automatically disable the LCD backlight in dark environments.
- **Hardware Watchdog:** Monitors the MQTT heartbeat; triggers a physical alarm (flickering LED cluster) if the Pi 5 is unreachable for >120 seconds.
- **Dynamic Messaging:** Supports a custom message format using delimiters to update the physical LCD lines remotely from the server.