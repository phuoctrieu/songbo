import streamlit as st
import asyncio
import websockets
import json
from datetime import datetime
import pandas as pd
import threading
import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Class thu thập dữ liệu từ thiết bị
class DeviceDataCollector:
    def __init__(self, device_ip="192.168.200.211:8880", username="ecapro", password="123456"):
        self.device_ip = device_ip
        self.username = username
        self.password = password

    def get_device_data(self):
        try:
            url = f"http://{self.device_ip}/index.htm"
            response = requests.get(
                url, 
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                device_info = {}
                measurements = {}
                
                # Parse thông tin thiết bị
                if len(tables) > 0:
                    for row in tables[0].find_all('tr'):
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 2:
                            key = cols[0].get_text(strip=True)
                            value = cols[1].get_text(strip=True)
                            device_info[key] = value
                
                # Parse dữ liệu đo
                if len(tables) > 1:
                    for row in tables[1].find_all('tr'):
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 2:
                            key = cols[0].get_text(strip=True)
                            value = cols[1].get_text(strip=True)
                            measurements[key] = value
                
                return {
                    'device_info': device_info,
                    'measurements': measurements
                }
            return None
        except Exception as e:
            logger.error(f"Error collecting data: {str(e)}")
            return None

# WebSocket Server
async def handle_client(websocket, path):
    collector = DeviceDataCollector()
    
    try:
        auth = await websocket.recv()
        auth_data = json.loads(auth)
        
        if auth_data['username'] == 'ecapro' and auth_data['password'] == '123456':
            logger.info("Client authenticated successfully")
            
            while True:
                data = collector.get_device_data()
                
                if data:
                    await websocket.send(json.dumps(data))
                else:
                    dummy_data = {
                        'device_info': {
                            'name': 'Device 1',
                            'status': 'Online'
                        },
                        'measurements': {
                            'temperature': '25.6',
                            'humidity': '65%'
                        }
                    }
                    await websocket.send(json.dumps(dummy_data))
                
                await asyncio.sleep(1)
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error in handle_client: {str(e)}")

async def start_websocket_server():
    server = await websockets.serve(
        handle_client, 
        "0.0.0.0",
        8880,
        ping_interval=None
    )
    logger.info("WebSocket server started on ws://0.0.0.0:8880")
    await server.wait_closed()

# Streamlit Client
async def connect_websocket(uri):
    try:
        async with websockets.connect(uri) as websocket:
            auth_message = {
                "username": "ecapro",
                "password": "123456"
            }
            await websocket.send(json.dumps(auth_message))
            data = await websocket.recv()
            return json.loads(data)
            
    except Exception as e:
        st.error(f"Lỗi kết nối WebSocket: {str(e)}")
        return None

def update_data():
    if 'data' not in st.session_state:
        st.session_state.data = None
    
    uri = "ws://localhost:8880"
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
        
        # Vẽ biểu đồ
        numeric_data = {}
        for key, value in data['measurements'].items():
            try:
                numeric_data[key] = float(value.replace('%', ''))
            except:
                continue
        if numeric_data:
            st.line_chart(numeric_data)

def run_streamlit():
    st.title("THÔNG TIN VẬN HÀNH THỦY VĂN NHÀ MÁY")
    
    if st.button("Refresh"):
        update_data()
    
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    current_time = datetime.now()
    if (current_time - st.session_state.last_refresh).seconds >= 5:
        update_data()
        st.session_state.last_refresh = current_time
    
    if hasattr(st.session_state, 'data') and st.session_state.data:
        display_data(st.session_state.data)
    else:
        st.warning("Đang kết nối...")

def run_websocket():
    asyncio.run(start_websocket_server())

if __name__ == "__main__":
    # Khởi động WebSocket server trong thread riêng
    websocket_thread = threading.Thread(target=run_websocket)
    websocket_thread.daemon = True  # Thread sẽ tự động kết thúc khi chương trình chính kết thúc
    websocket_thread.start()
    
    # Chạy Streamlit app trong main thread
    run_streamlit()
