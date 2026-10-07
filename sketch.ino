#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";
const char* MQTT_SERVER = "broker.hivemq.com"; 
const int MQTT_PORT = 1883;
const char* MQTT_TOPIC = "lab2/sensors/esp32_01/data";
const char* DEVICE_ID = "esp32_01";

const int DHT_PIN = 15;
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
DHTesp dht;
unsigned long lastSend = 0;
unsigned long sequenceNo = 0;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  dht.setup(DHT_PIN, DHTesp::DHT22);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
  
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setBufferSize(256);
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return NAN;
  return duration * 0.0343f / 2.0f;
}

void loop() {
  if (!mqttClient.connected()) {
    if (mqttClient.connect("ESP32-Lab2-Client")) {
      Serial.println("Connected to MQTT");
    }
  }
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastSend >= 5000) {
    lastSend = now;
    TempAndHumidity data = dht.getTempAndHumidity();
    float distance = readDistanceCm();

    if (isfinite(data.temperature) && isfinite(data.humidity) && isfinite(distance)) {
      sequenceNo++;
      char payload[256];
      snprintf(payload, sizeof(payload),
        "{\"device_id\":\"%s\",\"temperature\":%.2f,\"humidity\":%.2f,\"distance_cm\":%.2f,"
        "\"rssi\":%ld,\"sequence\":%lu,\"uptime_s\":%lu}",
        DEVICE_ID, data.temperature, data.humidity, distance, WiFi.RSSI(), sequenceNo, millis()/1000);
      
      mqttClient.publish(MQTT_TOPIC, payload);
      Serial.println(payload);
    }
  }
}