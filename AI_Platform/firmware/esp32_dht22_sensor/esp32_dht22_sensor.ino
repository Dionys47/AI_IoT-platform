/*
  ESP32 + DHT22 IoT Sensor
  Sends temperature and humidity to AI-IoT Platform.
  
  Wiring:
    DHT22 DATA pin -> GPIO 4  (or change DHTPIN below)
    DHT22 VCC       -> 3.3V
    DHT22 GND       -> GND

  Instructions:
    1. Install libraries: DHT sensor library by Adafruit, Adafruit Unified Sensor
    2. Open http://localhost:8000 -> Devices tab -> "Add Real WiFi Sensor"
    3. Copy the Device ID and API Key into the fields below
    4. Set your WiFi SSID and password below
    5. Set PLATFORM_HOST to your PC's local IP (ipconfig on Windows)
    6. Flash to ESP32
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ===== CONFIGURE THESE =====
const char* WIFI_SSID     = "D14";
const char* WIFI_PASSWORD = "delta0074";

const char* DEVICE_ID  = "wifi-89b8ac48";
const char* API_KEY    = "Ip3Fab91mwr2cDFFNmtH4lMw5FAI2O4n";

// IP of the machine running server_final.py
// If same WiFi, use local IP (run ipconfig, e.g. 192.168.x.x)
// If remote server, use its public IP
const char* PLATFORM_HOST = "10.136.134.249";
const int   PLATFORM_PORT = 8000;

#define DHTPIN 5          // GPIO pin connected to DHT22 data (D5)
#define DHTTYPE DHT22
#define SEND_INTERVAL 10  // seconds between readings

// Built-in LED on most ESP32 boards is GPIO 2
#define LED_PIN 2
// ============================

DHT dht(DHTPIN, DHTTYPE);

unsigned long lastSend = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("\n\nESP32 + DHT22 Sensor");
  Serial.print("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(LED_PIN, HIGH);
  } else {
    Serial.println("\nWiFi failed! Check credentials.");
  }

  dht.begin();
  Serial.println("DHT22 initialized");
  delay(500);
  digitalWrite(LED_PIN, LOW);
}

void loop() {
  // Reconnect WiFi if dropped
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    WiFi.disconnect();
    WiFi.reconnect();
    delay(5000);
    return;
  }

  unsigned long now = millis();
  if (now - lastSend < SEND_INTERVAL * 1000) {
    delay(100);
    return;
  }
  lastSend = now;

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read DHT22");
    return;
  }

  Serial.print("Temp: "); Serial.print(temperature); Serial.print(" C  ");
  Serial.print("Humidity: "); Serial.print(humidity); Serial.println(" %");

  // Send temperature
  sendData(temperature, "temperature", "C");
  delay(200);
  // Send humidity
  sendData(humidity, "humidity", "%");
}

void sendData(float value, const char* sensorType, const char* unit) {
  HTTPClient http;
  char url[80];
  snprintf(url, sizeof(url), "http://%s:%d/api/v1/ingest", PLATFORM_HOST, PLATFORM_PORT);

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Id", DEVICE_ID);
  http.addHeader("X-Device-Key", API_KEY);

  char body[120];
  snprintf(body, sizeof(body),
           "{\"value\":%.1f,\"sensor_type\":\"%s\",\"unit\":\"%s\"}",
           value, sensorType, unit);

  int code = http.POST(body);

  if (code == 200) {
    Serial.print("Sent "); Serial.print(sensorType);
    Serial.print(" -> HTTP ");
    Serial.println(code);
    blink(1);
  } else {
    Serial.print("Error "); Serial.print(sensorType);
    Serial.print(": HTTP ");
    Serial.println(code);
    blink(3);
  }
  http.end();
}

void blink(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
}
