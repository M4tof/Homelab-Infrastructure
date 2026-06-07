import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import setproctitle
from gpiozero import CPUTemperature
import psutil
import os

# Rename process for easier identification in monitoring (e.g., btop)
setproctitle.setproctitle("pico-broadcaster")

# --- CONFIG ---
BROKER = "127.0.0.1"
TOPIC = "lab/pi/status"

# --- CUSTOMIZATION ---
# This text will appear on the LCD line 2 for the first 30 seconds
CUSTOM_MESSAGE = "Server: OK"

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

print("Heartbeat active. Proof of Life broadcasting every 30s...")
msgCount = 0

while True:
    # 1. Get real time
    now_str = datetime.now().strftime("%H%M")

    if msgCount%2 == 0 :
        # Build JSON with the custom message
        payload_dict = {
            "7s": now_str,
            "a": 0,
            "c": CUSTOM_MESSAGE
        }
    else:
        # Build JSON without "c"
        payload_dict = {
            "7s": now_str,
            "a": 0
        }
    t = os.popen('vcgencmd measure_temp').readline()
    t = t.replace("temp=","").replace("'C\n","")
    CUSTOM_MESSAGE = f"T:{t}C HDD:{psutil.disk_usage('/mnt/external').percent:.0f}%|Ram:{psutil.virtual_memory().percent:.0f}% SSD:{psutil.disk_usage('/').percent:.0f}%"
    msgCount += 1

    payload = json.dumps(payload_dict)

    # 2. Send it!
    client.publish(TOPIC, payload)

    # Update console log
    status_msg = CUSTOM_MESSAGE if "c" in payload_dict else "Local Diag Mode"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent: {now_str} | Mode: {status_msg} | Count: {msgCount}")

    # 3. Precise sleep to trigger every 30 seconds
    time_to_sleep = 30 - (time.time() % 30)
    time.sleep(time_to_sleep)
