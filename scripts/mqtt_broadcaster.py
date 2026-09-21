import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import setproctitle
import subprocess
import psutil


# Rename process for easier identification in monitoring (e.g., btop)
setproctitle.setproctitle("pico-broadcaster")

# --- CONFIG ---
BROKER = "127.0.0.1"
TOPIC = "lab/pi/status"

# ==========================================
# HEALTH THRESHOLDS
# ==========================================
TEMP_WARN_C   = 70.0  # Blue LED threshold
TEMP_CRIT_C   = 80.0  # Red LED + NTFY threshold
DISK_WARN_PCT = 85.0  # Blue LED threshold
DISK_CRIT_PCT = 92.0  # Red LED + NTFY threshold
RAM_WARN_PCT  = 90.0  # Blue LED threshold

# LED States
LED_OFF      = 0
LED_RED_CRIT = 1
LED_GREEN_OK = 2
LED_BLUE_WRN = 3

def get_pi_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        return 0.0

def on_connect(client, userdata, flags, rc):
    """ Callback when connected to the broker """
    if rc == 0:
        print("Connected to Mosquitto successfully.")
    else:
        print(f"Connection failed with code {rc}")

# Setup MQTT Client
client = mqtt.Client()
client.on_connect = on_connect

# Connect to the broker
connected = False
print("Connecting to MQTT Broker...")
while not connected:
    try:
        client.connect(BROKER, 1883, 60)
        connected = True
        print("Successfully connected to MQTT Broker.")
    except Exception as e:
        print(f"MQTT Broker not ready yet ({e}). Retrying in 5s...")
        time.sleep(5)

# Start background network loop
client.loop_start()
print("Heartbeat active. Proof of Life broadcasting every 10s...")
msgCount = 0

while True:
    # 1. Get real time
    now_str = datetime.now().strftime("%H%M")

    CUSTOM_MESSAGE = ""
    alarm_state = LED_GREEN_OK  # Default: All systems healthy

    # -------------------------------------------------------------
    # 1. GATHER LOCAL PI 5 STATS
    # -------------------------------------------------------------
    pi_temp = get_pi_temp()
    try:
        hdd_pct = psutil.disk_usage('/mnt/EXTERNAL_HDD').percent
    except Exception:
        hdd_pct = 0.0
    ram_pct = psutil.virtual_memory().percent
    ssd_pct = psutil.disk_usage('/').percent

    # Evaluate Pi 5 Health
    if pi_temp >= TEMP_CRIT_C or ssd_pct >= DISK_CRIT_PCT or hdd_pct >= DISK_CRIT_PCT:
        alarm_state = LED_RED_CRIT
    elif pi_temp >= TEMP_WARN_C or ssd_pct >= DISK_WARN_PCT or hdd_pct >= DISK_WARN_PCT or ram_pct >= RAM_WARN_PCT:
        alarm_state = LED_BLUE_WRN

    # -------------------------------------------------------------
    # 2. SCREEN ROTATION & REMOTE STATS
    # -------------------------------------------------------------
    screen_idx = msgCount % 3

    # --- SCREEN 0: Pi 5 Local Stats ---
    if screen_idx == 0:
        CUSTOM_MESSAGE = f"T:{pi_temp:.1f}C HDD:{hdd_pct:.0f}%|Ram:{ram_pct:.0f}% SSD:{ssd_pct:.0f}%"

    # --- SCREEN 1: M700 Remote Stats ---
    elif screen_idx == 1:
        remote_cmd = (
            "sensors | grep -E 'Package id 0:|id 0:' | head -n 1 | awk -F'[+°]' '{print $2}'; "
            "df -h / | awk 'NR==2 {print $5}'; "
            "free -m | awk 'NR==2 {print $3,$2}'"
        )
        try:
            res = subprocess.run(
                ['ssh', '-q', '-o', 'ConnectTimeout=2', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no', 'USER@IP_ADDRS', remote_cmd],
                capture_output=True,
                text=True,
                timeout=3
            )
            ssh_output = res.stdout.splitlines()

            if len(ssh_output) >= 3:
                m700_temp = float(ssh_output[0].strip() or 0)
                m700_ssd = float(ssh_output[1].strip().replace('%', '') or 0)
                ram_data = ssh_output[2].split()
                m700_ram_pct = (int(ram_data[0]) / int(ram_data[1])) * 100
                CUSTOM_MESSAGE = f"M700 T:{m700_temp:.0f}C|SSD:{m700_ssd:.0f}% Ram:{m700_ram_pct:.0f}%"

                # Check M700 health only when it is actively running
                if m700_temp >= TEMP_CRIT_C or m700_ssd >= DISK_CRIT_PCT:
                    alarm_state = LED_RED_CRIT
                elif (m700_temp >= TEMP_WARN_C or m700_ssd >= DISK_WARN_PCT or m700_ram_pct >= RAM_WARN_PCT) and alarm_state != LED_RED_CRIT:
                    alarm_state = LED_BLUE_WRN

            else:
                # If command produced unexpected output
                CUSTOM_MESSAGE = "M700: Standby"

        except Exception:
            # M700 is powered off / unreachable -> Intended behavior, NOT an alert
            CUSTOM_MESSAGE = "M700: Offline|Standby"

    # --- SCREEN 2: Pico Onboard Diag Mode ---
    # Omitting "c" triggers the Pico's internal Lux, Temp & Free RAM view
    elif screen_idx == 2:
        CUSTOM_MESSAGE = ""

    # -------------------------------------------------------------
    # 3. PUBLISH PAYLOAD
    # -------------------------------------------------------------
    payload_dict = {
        "7s": now_str,
        "a": alarm_state
    }
    if CUSTOM_MESSAGE:
        payload_dict["c"] = CUSTOM_MESSAGE

    client.publish(TOPIC, json.dumps(payload_dict))

    # Console logging
    color_map = {0: "OFF", 1: "RED (CRIT)", 2: "GREEN (OK)", 3: "BLUE (WARN)"}
    screen_log = CUSTOM_MESSAGE if CUSTOM_MESSAGE else "Pico Internal Diag"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent: {now_str} | LED: {color_map.get(alarm_state)} | Mode: {screen_log}")

    msgCount += 1
    time_to_sleep = 10 - (time.time() % 10)
    time.sleep(time_to_sleep)
