import asyncio
import websockets
import json
import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup

class DeviceDataCollector:
    def __init__(self, device_ip="192.168.200.211:8880", username="ecapro", password="123456"):
        self.device_ip = device_ip
        self.username = username
        self.password = password

    def get_device_data(self):
        try:
            # Lấy dữ liệu từ thiết bị thực
            url = f"http://{self.device_ip}/index.htm"
            response = requests.get(
                url, 
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                # Parse HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Lấy dữ liệu từ các bảng
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
            print(f"Error collecting data: {str(e)}")
            return None

async def handle_client(websocket, path):
    collector = DeviceDataCollector()
    
    try:
        # Xử lý xác thực
        auth = await websocket.recv()
        auth_data = json.loads(auth)
        
        if auth_data['username'] == 'ecapro' and auth_data['password'] == '123456':
            print("Client authenticated successfully")
            
            while True:
                # Lấy dữ liệu thực từ thiết bị
                data = collector.get_device_data()
                
                if data:
                    # Gửi dữ liệu qua WebSocket
                    await websocket.send(json.dumps(data))
                else:
                    # Gửi dữ liệu mẫu nếu không lấy được dữ liệu thực
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
                
                # Đợi 1 giây trước khi gửi dữ liệu tiếp theo
                await asyncio.sleep(1)
                
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {str(e)}")

async def main():
    server = await websockets.serve(
        handle_client, 
        "0.0.0.0",  # Lắng nghe tất cả các interface
        8880,       # Port
        ping_interval=None  # Tắt ping/pong để tránh timeout
    )
    print("WebSocket server started on ws://0.0.0.0:8880")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
