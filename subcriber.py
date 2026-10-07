import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Cấu hình MQTT Broker (Public) ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "lab2/sensors/esp32_01/data"

# --- Cấu hình InfluxDB 2.x ---
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "lMUAIUqTVe2VVM2zKM9PeYD_o7nik9ouMLX-cBtlACeFiuB2wawMqZx30N7iGHVlGqsUz8lu7ViFIGyNbwmUfg=="
INFLUX_ORG = "ptit_iot"      # Đã cập nhật theo cấu hình của bạn
INFLUX_BUCKET = "iot_data"   # Bucket lưu trữ

# Khởi tạo client InfluxDB
client_db = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client_db.write_api(write_options=SYNCHRONOUS)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Đã kết nối MQTT Broker: {MQTT_BROKER}")
        client.subscribe(MQTT_TOPIC)
        print(f"Đang theo dõi topic: {MQTT_TOPIC}")
    else:
        print(f"Kết nối thất bại, mã lỗi {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        
        # Validate dữ liệu đầu vào
        if data.get('temperature') is None or data.get('humidity') is None:
            return

        # Thiết kế schema lưu trữ
        point = Point("environment") \
            .tag("device_id", data.get("device_id", "unknown")) \
            .field("temperature", float(data["temperature"])) \
            .field("humidity", float(data["humidity"])) \
            .field("distance_cm", float(data["distance_cm"])) \
            .field("rssi", int(data.get("rssi", 0))) \
            .field("sequence", int(data.get("sequence", 0)))
        
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print("-> Đã lưu vào database:", data)

    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"Lỗi ghi dữ liệu: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

print("Đang khởi động Subscriber...")
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_forever()