import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient

# Thiết lập UI Dashboard
st.set_page_config(page_title="IoT Monitoring Dashboard", layout="wide")
st.title("Dashboard Giám Sát Dữ Liệu IoT")

# ==========================================
# CẤU HÌNH INFLUXDB 2.X
# ==========================================
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "lMUAIUqTVe2VVM2zKM9PeYD_o7nik9ouMLX-cBtlACeFiuB2wawMqZx30N7iGHVlGqsUz8lu7ViFIGyNbwmUfg=="
INFLUX_ORG = "ptit_iot"
INFLUX_BUCKET = "iot_data"

@st.cache_resource
def init_client():
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

client = init_client()
query_api = client.query_api()

# Hàm xử lý chung để tránh lỗi trả về List từ InfluxDB và pivot dữ liệu
def get_pivoted_dataframe(query):
    df = query_api.query_data_frame(query, org=INFLUX_ORG)
    if isinstance(df, list):
        if len(df) > 0:
            df = pd.concat(df, ignore_index=True)
        else:
            df = pd.DataFrame()
    
    if not df.empty:
         # Sắp xếp lại dataframe, loại bỏ các cột không cần thiết của InfluxDB
         drop_cols = ['result', 'table', '_start', '_stop', '_measurement']
         df = df.drop(columns=[col for col in drop_cols if col in df.columns])
         
         # Chuyển cột _time thành index
         if '_time' in df.columns:
             df.set_index('_time', inplace=True)
    return df

# Chia làm 2 cột hiển thị
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌡️ Dữ liệu thô Real-time (Dạng bảng)")
    # Truy vấn dữ liệu thô (pivot để các fields thành cột)
    query_raw = f'''
        from(bucket: "{INFLUX_BUCKET}") 
        |> range(start: -15m) 
        |> filter(fn: (r) => r["_measurement"] == "environment")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    try:
        df_raw = get_pivoted_dataframe(query_raw)
        if not df_raw.empty:
            st.dataframe(df_raw, use_container_width=True)
        else:
            st.info("Đang chờ dữ liệu thô... Hãy cho ESP32 chạy!")
    except Exception as e:
        st.error(f"Lỗi lấy dữ liệu: {e}")

with col2:
    st.subheader("⚙️ Dữ liệu đã Tiền xử lý (Dạng bảng)")
    # Truy vấn dữ liệu đã tiền xử lý (pivot)
    query_proc = f'''
        from(bucket: "{INFLUX_BUCKET}") 
        |> range(start: -1h) 
        |> filter(fn: (r) => r["_measurement"] == "environment_processed")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    try:
        df_proc = get_pivoted_dataframe(query_proc)
        if not df_proc.empty:
            st.dataframe(df_proc, use_container_width=True)
        else:
            st.info("Hãy chạy file preprocess.py trước để có dữ liệu sạch.")
    except Exception as e:
        st.error(f"Lỗi lấy dữ liệu: {e}")