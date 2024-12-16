import streamlit as st
import asyncio
import websockets
import json
from datetime import datetime
import pandas as pd

async def connect_websocket(uri):
    try:
        async with websockets.connect(uri) as websocket:
            # Gửi thông tin xác thực
            auth_message = {
                "username": "ecapro",
                "password": "123456"
            }
            await websocket.send(json.dumps(auth_message))
            
            # Nhận dữ liệu
            data = await websocket.recv()
            return json.loads(data)
            
    except Exception as e:
        st.error(f"Lỗi kết nối WebSocket: {str(e)}")
        return None

def update_data():
    if 'data' not in st.session_state:
        st.session_state.data = None
    
    # Kết nối WebSocket
    uri = "ws://192.168.200.211:8880"
    new_data = asyncio.run(connect_websocket(uri))
    
    if new_data:
        st.session_state.data = new_data

def display_data(data):
    if not data:
        st.warning("Không có dữ liệu")
        return
    
    # Hiển thị thông tin thiết bị
    st.subheader("Thông tin thiết bị")
    if 'device_info' in data:
        for key, value in data['device_info'].items():
            st.text(f"{key}: {value}")
    
    # Hiển thị dữ liệu đo
    st.subheader("Dữ liệu đo")
    if 'measurements' in data:
        df = pd.DataFrame(data['measurements'].items(), columns=['Metric', 'Value'])
        st.dataframe(df)
        
        # Vẽ biểu đồ nếu có dữ liệu số
        numeric_data = {}
        for key, value in data['measurements'].items():
            try:
                numeric_data[key] = float(value.replace('%', ''))
            except:
                continue
        if numeric_data:
            st.line_chart(numeric_data)

def main():
    st.title("THÔNG TIN VẬN HÀNH THỦY VĂN NHÀ MÁY")
    
    # Tạo nút refresh
    if st.button("Refresh"):
        update_data()
    
    # Auto refresh mỗi 5 giây
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    current_time = datetime.now()
    if (current_time - st.session_state.last_refresh).seconds >= 5:
        update_data()
        st.session_state.last_refresh = current_time
    
    # Hiển thị dữ liệu
    if hasattr(st.session_state, 'data') and st.session_state.data:
        display_data(st.session_state.data)
    else:
        st.warning("Đang kết nối...")

if __name__ == "__main__":
    main()
