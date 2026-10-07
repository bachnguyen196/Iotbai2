import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ==========================================
# CẤU HÌNH INFLUXDB 2.X
# ==========================================
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "lMUAIUqTVe2VVM2zKM9PeYD_o7nik9ouMLX-cBtlACeFiuB2wawMqZx30N7iGHVlGqsUz8lu7ViFIGyNbwmUfg=="
INFLUX_ORG = "ptit_iot"
INFLUX_BUCKET = "iot_data"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

print("Đang truy vấn dữ liệu thô từ InfluxDB...")

# Truy vấn dữ liệu 1 giờ qua
query = f'''
    from(bucket: "{INFLUX_BUCKET}")
    |> range(start: -1h)
    |> filter(fn: (r) => r["_measurement"] == "environment")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
df = query_api.query_data_frame(query, org=INFLUX_ORG)

# --- FIX 1: Xử lý trường hợp InfluxDB trả về một List các DataFrame ---
if isinstance(df, list):
    if len(df) > 0:
        df = pd.concat(df, ignore_index=True)
    else:
        df = pd.DataFrame() # Tạo DataFrame rỗng nếu list trống

# --- KIỂM TRA DATAFRAME CÓ DỮ LIỆU ---
if df is not None and not df.empty:
    if '_time' in df.columns:
        df.set_index('_time', inplace=True)
    
    # Lọc chỉ lấy các cột cần thiết
    cols_to_keep = ['temperature', 'humidity', 'distance_cm']
    existing_cols = [col for col in cols_to_keep if col in df.columns]
    df = df[existing_cols]

    # 1. Xử lý giá trị thiếu (missing values) bằng nội suy
    df = df.interpolate(method='time')

    # 2. Phát hiện outlier bằng Z-score
    z_scores = np.abs((df - df.mean(numeric_only=True)) / df.std(numeric_only=True))
    df_clean = df[(z_scores < 3).all(axis=1)]

    # 3. Resampling theo cửa sổ thời gian (1 phút)
    # --- FIX 2: Thay '1T' thành '1min' theo chuẩn Pandas mới ---
    df_resampled = df_clean.resample('1min').mean().dropna()

    # --- FIX 3: Đảm bảo dữ liệu sau resampling không bị rỗng trước khi chuẩn hóa ---
    if not df_resampled.empty:
        # 4. Tạo đặc trưng đơn giản & chuẩn hóa
        df_resampled['temp_rolling_mean'] = df_resampled['temperature'].rolling(window=3).mean().bfill()
        scaler = StandardScaler()
        df_resampled[['temp_scaled', 'hum_scaled']] = scaler.fit_transform(df_resampled[['temperature', 'humidity']])

        # 5. Lưu kết quả tiền xử lý vào measurement mới
        for index, row in df_resampled.iterrows():
            p = Point("environment_processed") \
                .tag("device_id", "esp32_01") \
                .field("temperature_clean", float(row['temperature'])) \
                .field("temp_rolling_mean", float(row['temp_rolling_mean'])) \
                .field("temp_scaled", float(row['temp_scaled'])) \
                .field("humidity_clean", float(row['humidity']))
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p, time=index)
        
        print("-> Đã tiền xử lý thành công và lưu vào measurement 'environment_processed'!")
    else:
        print("Cảnh báo: Dữ liệu bị rỗng sau bước lọc Outlier (Z-score) hoặc Resampling.")
        print("Gợi ý: Dữ liệu của bạn có thể đang dao động quá mạnh bị coi là nhiễu, hoặc có quá ít dữ liệu. Hãy sinh thêm dữ liệu thô từ ESP32.")
else:
    print("Chưa có dữ liệu thô trong 1 giờ qua.")
    print("Gợi ý: Hãy bật file subscriber.py và cho ESP32 (Wokwi) gửi thêm dữ liệu lên, chờ khoảng 1-2 phút rồi chạy lại file này.")