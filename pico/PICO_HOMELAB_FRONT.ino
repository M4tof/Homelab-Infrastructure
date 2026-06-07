/**
 * Project: Secure Edge HomeLab - Satellite Telemetry Node
 * Hardware: Raspberry Pi Pico 2 W (RP2350)
 * Description: Dual-core firmware managing a physical dashboard.
 *              Core 0: Handles WiFi, MQTT, ntfy.sh alerts, and LCD I2C.
 *              Core 1: High-speed multiplexing for 7-Segment display.
 * License: Apache 2.0
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <HTTPClient.h>
#include "secrets.h" // Import your credentials !!!

#define FIRMWARE_VERSION 5 //Personal note, to see if firmware updates succesfully

// ==========================================
// 1. CONFIGURATION & NETWORK SETUP
// ==========================================
const char* WIFI_SSID     = SECRET_SSID;
const char* WIFI_PASSWORD = SECRET_PASS;
const char* MQTT_SERVER   = SECRET_MQTT_SERVER;
const char* MQTT_TOPIC    = "lab/pi/status";
const char* NTFY_TOPIC    = SECRET_NTFY_TOPIC;
const char* DISPLAYN   = DISPLAY_NAME;

// ==========================================
// 2. HARDWARE PIN MAPPING
// ==========================================
// 7-Segment Pins (Common Anode/Cathode depending on wiring)
const int DIGITS[]   = {16, 19, 20, 11};           // Pins controlling which digit is ON
const int ALL_SEGS[] = {17, 21, 13, 14, 15, 18, 12}; // Pins controlling A-G segments
const int ALARM_PIN  = 10;                         // Physical LED or Buzzer pin
const int SEG_DP     = 9;                          // Decimal point pin
const int PHOTO_RES_PIN  = 26;                          // Photoresistor pin

// LCD Initialization (Address 0x27, 16 columns, 2 rows)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ==========================================
// 3. GLOBAL STATE & SHARED VARIABLES
// ==========================================
volatile int displayNumbers[4] = {0, 0, 0, 0}; // Numbers currently on the 7-segment
volatile unsigned long lastHeartbeat = 0;     // Timestamp of last MQTT message
volatile unsigned long lastLocalTick = 0;     // Timestamp for the 1-minute internal clock
volatile unsigned long lastDiagSend = 0;      // Timestamp for Serial diagnostics
volatile unsigned long lastLCDUpdate = 0;     // Timestamp for last custome "c" message
volatile int currentLightLevel = 0;           // Detected 'light value' in the room
bool alertSent = false;                       // Prevents spamming NTFY notifications
bool manualAlertActive = false;               // Manual Alert signal from RPI
bool manualJustLED = false;

int local_hh = 0; // Current hour
int local_mm = 0; // Current minute

// Backlight Management
// 0 = Off, 1 = On, 2 = Auto (Sensor)
int backlightMode = 2; 
const int LIGHT_THRESHOLD = 150; 

// Custom Message Tracking
String currentCustomMsg = "";
char MsgDelimiter = '|';
unsigned long customMsgTimestamp = 0;
const unsigned long CUSTOM_MSG_TIMEOUT = 30000; // 30 seconds

// Map numbers 0-9 and Clear to 7-segment segment states
const bool NUM_MAP[11][7] = { 
  {1, 1, 1, 1, 1, 1, 0}, {0, 1, 1, 0, 0, 0, 0}, {1, 1, 0, 1, 1, 0, 1},
  {1, 1, 1, 1, 0, 0, 1}, {0, 1, 1, 0, 0, 1, 1}, {1, 0, 1, 1, 0, 1, 1},
  {1, 0, 1, 1, 1, 1, 1}, {1, 1, 1, 0, 0, 0, 0}, {1, 1, 1, 1, 1, 1, 1},
  {1, 1, 1, 1, 0, 1, 1}, {0, 0, 0, 0, 0, 0, 0}
};

WiFiClient picoClient;
PubSubClient mqtt(picoClient);

// ==========================================
// 4. LOGIC FUNCTIONS
// ==========================================

/**
 * Prints system health to the Serial Monitor for debugging
 */
void printDiagnostics() {
    int lightLevel = checkLocalLight(); 

    Serial.println("\n--- PICO DIAGNOSTIC REPORT ---");
    Serial.print(FIRMWARE_VERSION);
    Serial.println("V Firmware version");
    Serial.print("Uptime: "); Serial.print(millis() / 1000); Serial.println("s");
    Serial.print("WiFi: ");
    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("CONNECTED | Signal: "); Serial.print(WiFi.RSSI()); Serial.println(" dBm");
    } else {
        Serial.println("DISCONNECTED");
    }
    
    Serial.print("MQTT: "); Serial.println(mqtt.connected() ? "CONNECTED" : "DISCONNECTED");
    Serial.print("Backlight Mode: "); Serial.println(backlightMode);
    Serial.print("Current Light Level: "); Serial.println(lightLevel); // <--- SEE THE VALUE HERE

    long secondsSincePi = (millis() - lastHeartbeat) / 1000;
    Serial.print("Last Pi Heartbeat: "); Serial.print(secondsSincePi); Serial.println("s ago");
    Serial.println("------------------------------");
}

/**
 * Sends a push notification via NTFY.sh
 */
void sendNtfyAlert(String message) {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = "http://ntfy.sh/" + String(NTFY_TOPIC);
        http.begin(url);
        http.POST(message);
        http.end();
        Serial.println(">>> [ntfy] Alert Sent: " + message);
    }
}

/**
 * Checks the brightness in the room.
 */
int checkLocalLight(){
  long value = 0;
  for(int i = 0; i < 10; i++){
    value += analogRead(PHOTO_RES_PIN);
  }
  return (int)(value / 10);
}

/**
 * Splits local time into individual digits for the 7-segment array
 */
void updateDisplayNumbers() {
    displayNumbers[0] = local_hh / 10;
    displayNumbers[1] = local_hh % 10;
    displayNumbers[2] = local_mm / 10;
    displayNumbers[3] = local_mm % 10;
}

/**
 * Updates the LCD with custom message from the RPI, or local diagnostic if no new "c" in defined time
 */
void updateLCD() {
    bool isCustomActive = (currentCustomMsg.length() > 0) && (millis() - customMsgTimestamp < CUSTOM_MSG_TIMEOUT);

    if (isCustomActive) {
        int delimiterIndex = currentCustomMsg.indexOf(MsgDelimiter);
        
        if (delimiterIndex == -1) {
            lcd.setCursor(0, 0);
            lcd.print(DISPLAYN);
            lcd.setCursor(0, 1);
            lcd.print("                "); // Clear line
            lcd.setCursor(0, 1);
            lcd.print(currentCustomMsg.substring(0, 16));
        } 
        else {
            String line1 = currentCustomMsg.substring(0, delimiterIndex);
            String line2 = currentCustomMsg.substring(delimiterIndex + 1);

            lcd.setCursor(0, 0);
            lcd.print("                "); // Clear
            lcd.setCursor(0, 0);
            lcd.print(line1.substring(0, 16));

            lcd.setCursor(0, 1);
            lcd.print("                "); // Clear
            lcd.setCursor(0, 1);
            lcd.print(line2.substring(0, 16));
        }
        
    } 
    else {
        int delta = currentLightLevel - LIGHT_THRESHOLD;
        char l1[17];
        // Format: "Delta Light: +450" or "Delta Light: -120"
        // %-5d ensures the number has space and doesn't leave "ghost" digits
        snprintf(l1, sizeof(l1), "Delta L: %-5d", delta);
        lcd.setCursor(0, 0);
        lcd.print("                ");
        lcd.setCursor(0, 0);
        lcd.print(l1);

        // --- LINE 2 LOGIC ---
        float temp = analogReadTemp();
        uint32_t totalRAM = 520 * 1024;
        uint32_t freeRAM = rp2040.getFreeHeap();
        int usedPercent = ((totalRAM - freeRAM) * 100) / totalRAM;

        char l2[17];
        snprintf(l2, sizeof(l2), "T:%.1fC RAM:%d%%  ", temp, usedPercent);
        lcd.setCursor(0, 1);
        lcd.print("                ");
        lcd.setCursor(0, 1);
        lcd.print(l2);
    }
}


/**
 * MQTT Callback: Triggered when a message arrives on the subscribed topic
 */
void callback(char* t, byte* payload, unsigned int length) {
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.print("JSON Parse failed: "); Serial.println(error.c_str());
    return;
  }

  // 1. Process 7-Segment Time ("7s" key)
  if (doc.containsKey("7s")) {
    const char* timeData = doc["7s"];
    if (strlen(timeData) == 4) {
      local_hh = (timeData[0] - '0') * 10 + (timeData[1] - '0');
      local_mm = (timeData[2] - '0') * 10 + (timeData[3] - '0');
      
      lastHeartbeat = millis();
      lastLocalTick = millis(); 
      updateDisplayNumbers();
      
      if (alertSent) {
          sendNtfyAlert("RPi 5 Heartbeat Restored. System back to normal.");
          alertSent = false;
      }
    }
  }

  // 2. Process Alarm Status ("a")
  if (doc.containsKey("a")) {
      int status = doc["a"];
      switch(status){
        case 0:     // Manual Clear Alert
            manualAlertActive = false;
            // If we were in an alert state and it's now 0, reset ntfy flag
            if (alertSent) {
                sendNtfyAlert("System Status: OK (Manual Clear)");
                alertSent = false;
            }
            break;
        case 1: // Raise Alert Real
            manualAlertActive = true;
            Serial.println("!!! ALERT: Pi reported status 1 (CRITICAL) !!!");
            break;
        case 2:   // Raise Alert, just LED
            manualJustLED = true;
            break;
        default:  // Lower Alert, just LED
            manualJustLED = false;
            break;
      }

  }

  // 3. Process Custom LCD Message ("c" key)
  if (doc.containsKey("c")) {
      currentCustomMsg = doc["c"].as<String>();
      customMsgTimestamp = millis();
      updateLCD(); // Immediate refresh
  } else {
      currentCustomMsg = ""; // Clear if 'c' is missing
  }

  
  // 4. Manual Backlight ("b": 0=Off, 1=On, 2=Auto)
  if (doc.containsKey("b")) {
      backlightMode = doc["b"];
      Serial.print("Backlight Mode set to: "); Serial.println(backlightMode);
  }
  
}

void setup_wifi() {
  lcd.setCursor(0,1); lcd.print("WiFi Connect...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }
  lcd.setCursor(0,1); lcd.print("WiFi OK!        ");
}

void reconnect() {
  if (!mqtt.connected()) {
    if (mqtt.connect("PicoSatelliteNode")) {
      mqtt.subscribe(MQTT_TOPIC);
    } else {
      delay(5000);
    }
  }
}

// ==========================================
// 5. CORE 0: NETWORK, LOGIC & LCD (Main Loop)
// ==========================================
void setup() {
  Serial.begin(115200); 
  
  delay(2000);
  Serial.println("================================");
  Serial.println(FIRMWARE_VERSION);
  Serial.println("================================");

  pinMode(ALARM_PIN, OUTPUT);
  analogReadResolution(12);
  
  // LCD Init
  Wire.setSDA(4); Wire.setSCL(5); Wire.begin();
  lcd.init(); lcd.backlight();
  lcd.setCursor(0,0); lcd.print(DISPLAYN);
  lcd.setCursor(0,1); lcd.print("Booting...");

  setup_wifi();
  mqtt.setServer(MQTT_SERVER, 1883);
  mqtt.setCallback(callback);
  
  lastHeartbeat = millis();
  lastLocalTick = millis();
  lastDiagSend = millis();
}


void loop() {
  if (!mqtt.connected()) reconnect();
  mqtt.loop();

  // 0. gather local sensor data
  currentLightLevel = checkLocalLight();

  // 1. Increment time locally if no MQTT update for 1 minute
  if (millis() - lastLocalTick >= 60000) {
      local_mm++;
      if (local_mm > 59) { local_mm = 0; local_hh++; }
      if (local_hh > 23) { local_hh = 0; }
      updateDisplayNumbers();
      lastLocalTick = millis();
  }

  // 2. WATCHDOG & ALARM, if RPI sends manual alarm or if RPI detected as down
  bool watchdogTimeout = (millis() - lastHeartbeat > 120000);

  if (watchdogTimeout || manualAlertActive) {
    digitalWrite(ALARM_PIN, HIGH);
    
    if (!alertSent) {
        String reason = watchdogTimeout ? "Watchdog Timeout" : "Pi Status 1";
        sendNtfyAlert("CRITICAL: " + reason);
        
        // Visual feedback on LCD
        lcd.setCursor(0, 1);
        lcd.print("!! SYSTEM ALRT !!");
        alertSent = true;
    }
  } 
  else if (manualJustLED){
    digitalWrite(ALARM_PIN, HIGH);
  } 
  else {
    digitalWrite(ALARM_PIN, LOW);
  }

    // 3. Backlight Smart Logic
  if (backlightMode == 0) {
      lcd.noBacklight();
  } else if (backlightMode == 1) {
      lcd.backlight();
  } else {
      // Mode 2: Auto
      int light = checkLocalLight();
      
      // Using a 100-unit "Deadzone" (Hysteresis) to prevent flickering
      if (currentLightLevel < (LIGHT_THRESHOLD - 50)) lcd.noBacklight(); 
      else if (currentLightLevel > (LIGHT_THRESHOLD + 50)) lcd.backlight();
  }
  
  // 4. LCD Refresh Timer (Every 5 seconds)
  if (millis() - lastLCDUpdate > 5000) {
      updateLCD();
      lastLCDUpdate = millis();
  }
  
  // 5. Periodic Diagnostics
  if (millis() - lastDiagSend > 10000) {
      printDiagnostics();
      lastDiagSend = millis();
  }
  
  delay(100); 
}

// ==========================================
// 6. CORE 1: 7-SEGMENT DISPLAY (Multiplexing)
// ==========================================
void setup1() {
  for (int i = 0; i < 7; i++) pinMode(ALL_SEGS[i], OUTPUT);
  for (int i = 0; i < 4; i++) pinMode(DIGITS[i], OUTPUT);
  pinMode(SEG_DP, OUTPUT);
}

void showDigit(int num, int pos) {
  // Turn off all digits first (prevent ghosting)
  for (int i = 0; i < 4; i++) digitalWrite(DIGITS[i], LOW);
  
  // Set the segments for the specific number
  for (int s = 0; s < 7; s++) {
    digitalWrite(ALL_SEGS[s], NUM_MAP[num][s] ? LOW : HIGH);
  }
  
  // Handle Decimal Point (usually between HH and MM)
  digitalWrite(SEG_DP, (pos == 1) ? LOW : HIGH); 
  
  // Turn on the specific digit
  digitalWrite(DIGITS[pos], HIGH);
}

void loop1() {
  // Fast multiplexing cycle
  for (int i = 0; i < 4; i++) {
    showDigit(displayNumbers[i], i);
    delay(2); 
  }
}