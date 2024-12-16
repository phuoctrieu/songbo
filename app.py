import streamlit as st
import io
import pandas as pd
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
import re
from bs4 import BeautifulSoup
import time

def connect_webiopi(host, username, password):
    try:
        url = f"http://{host}"
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        if response.status_code == 200:
            return True
        else:
            st.error(f"Lỗi xác thực: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Lỗi kết nối server: {str(e)}")
        return False

def parse_network_settings(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    settings = {}
    
    # Parse input fields
    input_fields = soup.find_all('input')
    for field in input_fields:
        field_id = field.get('id')
        if field_id:
            settings[field_id] = {
                'value': field.get('value', ''),
                'type': field.get('type', ''),
                'disabled': field.get('disabled') is not None
            }
    
    # Organize settings by category
    categories = {
        'network': ['mac', 'hostname', 'dhcp', 'vina3g', 'ip', 'gateway', 'mask', 'dns1', 'dns2'],
        'email': ['mailserver', 'mailport', 'mailfrom', 'mailpass', 'mailto0', 'mailto1', 'mailto2'],
        'ftp1': ['serverftp', 'filenameftp', 'pathftp', 'userftp', 'passftp'],
        'ftp2': ['serverftp2', 'pathftp2', 'userftp2', 'passftp2'],
        'sms': ['tel0', 'tel1', 'tel2', 'tel3', 'tel4'],
        'admin': ['username', 'newpass', 'conpass']
    }
    
    organized_settings = {}
    for category, fields in categories.items():
        organized_settings[category] = {
            field: settings.get(field, {}) for field in fields
        }
    
    return organized_settings

def parse_home_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}
    
    # Parse các thông tin từ trang Home
    try:
        # Tìm tất cả các table
        tables = soup.find_all('table')
        
        # Parse thông tin thiết bị
        device_info = {}
        if len(tables) > 0:
            rows = tables[0].find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    label = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    device_info[label] = value
        data['device_info'] = device_info
        
        # Parse thông tin đo đạc
        measurements = {}
        if len(tables) > 1:
            rows = tables[1].find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    label = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    measurements[label] = value
        data['measurements'] = measurements
        
    except Exception as e:
        st.error(f"Lỗi parse dữ liệu Home: {str(e)}")
    
    return data

def get_device_info(host, username, password):
    try:
        endpoints = {
            "Home": "/index.htm",  # Thêm endpoint Home
            "Network": "/networksetting.html",
            "Modbus": "/modbussetting.htm",
            "Calibration": "/calibrationsetting.htm",
            "Functions": "/functionssetting.htm", 
            "ModbusTCP": "/modbustcp.htm",
            "IO": "/iosetting.htm"
        }
        
        device_data = {}
        
        for name, endpoint in endpoints.items():
            url = f"http://{host}{endpoint}"
            response = requests.get(url, auth=HTTPBasicAuth(username, password))
            
            if response.status_code == 200:
                device_data[name] = {
                    'content': response.text,
                    'endpoint': endpoint
                }
                
                if name == "Network":
                    device_data[name]['settings'] = parse_network_settings(response.text)
                elif name == "Home":
                    device_data[name]['data'] = parse_home_data(response.text)
                
        return device_data
        
    except Exception as e:
        st.error(f"Lỗi lấy thông tin thiết bị: {str(e)}")
        return None

def display_network_settings(settings):
    # Network Settings
    st.subheader("Network Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"MAC Address: {settings['network']['mac']['value']}")
        st.text_input("Hostname", value=settings['network']['hostname']['value'])
        st.checkbox("DHCP", value=settings['network']['dhcp'].get('value')=='1')
    with col2:
        st.text_input("IP Address", value=settings['network']['ip']['value'])
        st.text_input("Gateway", value=settings['network']['gateway']['value'])
        st.text_input("Subnet Mask", value=settings['network']['mask']['value'])
    
    # Email Settings
    st.subheader("Email Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("SMTP Server", value=settings['email']['mailserver']['value'])
        st.text_input("From", value=settings['email']['mailfrom']['value'])
    with col2:
        st.text_input("Port", value=settings['email']['mailport']['value'])
        st.text_input("To", value=settings['email']['mailto0']['value'])
    
    # FTP Settings
    st.subheader("FTP Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("FTP1 Server", value=settings['ftp1']['serverftp']['value'])
        st.text_input("FTP1 User", value=settings['ftp1']['userftp']['value'])
    with col2:
        st.text_input("FTP2 Server", value=settings['ftp2']['serverftp2']['value'])
        st.text_input("FTP2 User", value=settings['ftp2']['userftp2']['value'])
    
    # SMS Settings
    st.subheader("SMS Settings")
    for i in range(5):
        st.text_input(f"Phone {i+1}", value=settings['sms'][f'tel{i}']['value'])

def display_home_data(data, host, device_info):
    if not data:
        st.warning("Không có dữ liệu")
        return
    
    url = f"http://{host}{device_info['Home']['endpoint']}"
    #st.markdown(f"[Mở trang Home trong tab mới]({url})")  # Giữ lại link để mở trong tab mới
    
    # Tạo HTML iframe
    iframe_html = f'<iframe src="{url}" width="100%" height="600" frameborder="0"></iframe>'
    st.components.v1.html(iframe_html, height=600, scrolling=True)

def main():
    st.title("WebIOPi Device Manager")
    
    # Thông tin đăng nhập mặc định
    host = "192.168.200.211:8880"
    username = "ecapro"
    password = "123456"
    
    # Tự động kết nối khi khởi động ứng dụng
    if connect_webiopi(host, username, password):
        st.success("Kết nối thành công!")
        
        device_info = get_device_info(host, username, password)
        
        if device_info:
            if 'Home' in device_info:
                display_home_data(device_info['Home']['data'], host, device_info)
            else:
                st.warning("Không thể lấy thông tin Home")
    else:
        st.error("Không thể kết nối đến server")

if __name__ == "__main__":
    main()
