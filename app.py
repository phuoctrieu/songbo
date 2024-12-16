import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import os
import google.generativeai as genai
import streamlit.components.v1 as components

# Cấu hình API keys
OPENWEATHER_API_KEY = "54f2addc6568b792dfd3c21aefb08794"
GEMINI_API_KEY = "AIzaSyD5IHMw1D80L9dMluUJ9DYczQwEIX60EWk"

# Cấu hình Gemini
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

def get_weather_data(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=vi"
    response = requests.get(url)
    return response.json()

def analyze_weather_data(data):
    weather_list = []
    
    for item in data['list']:
        weather_info = {
            'Thời gian': datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d %H:%M:%S'),
            'Nhiệt độ (°C)': round(item['main']['temp'], 1),
            'Cảm giác như (°C)': round(item['main']['feels_like'], 1),
            'Nhiệt độ min (°C)': round(item['main']['temp_min'], 1),
            'Nhiệt độ max (°C)': round(item['main']['temp_max'], 1),
            'Độ ẩm (%)': item['main']['humidity'],
            'Áp suất (hPa)': item['main']['pressure'],
            'Tốc độ gió (m/s)': item['wind']['speed'],
            'Hướng gió (độ)': item['wind'].get('deg', 0),
            'Mây (%)': item['clouds']['all'],
            'Mô tả': item['weather'][0]['description']
        }
        if 'rain' in item:
            weather_info['Lượng mưa (mm)'] = item['rain'].get('3h', 0)
        else:
            weather_info['Lượng mưa (mm)'] = 0
            
        weather_list.append(weather_info)
    
    return pd.DataFrame(weather_list)

def get_ai_analysis(df):
    # Chuẩn bị dữ liệu để gửi cho AI
    latest_data = df.iloc[0]
    
    # Tính toán thống kê cho từng ngày
    df['Date'] = pd.to_datetime(df['Thời gian']).dt.date
    daily_stats = df.groupby('Date').agg({
        'Nhiệt độ (°C)': ['min', 'max', 'mean'],
        'Độ ẩm (%)': 'mean',
        'Áp suất (hPa)': 'mean',
        'Tốc độ gió (m/s)': 'mean',
        'Mây (%)': 'mean',
        'Lượng mưa (mm)': 'sum'
    }).round(1)

    # Tạo prompt chi tiết hơn
    prompt = f"""
    Với vai trò là chuyên gia dự báo thời tiết, hãy phân tích dữ liệu thời tiết sau và đưa ra dự báo:
    
    Dữ liệu hiện tại ({latest_data['Thời gian']}):
    - Nhiệt độ: {latest_data['Nhiệt độ (°C)']}°C
    - Độ ẩm: {latest_data['Độ ẩm (%)']}%
    - Áp suất: {latest_data['Áp suất (hPa)']} hPa
    - Tốc độ gió: {latest_data['Tốc độ gió (m/s)']} m/s
    - Mây: {latest_data['Mây (%)']}%
    - Lượng mưa: {latest_data['Lượng mưa (mm)']} mm
    
    Thống kê theo ngày trong 5 ngày tới:
    """
    
    # Thêm thống kê từng ngày vào prompt
    for date, stats in daily_stats.iterrows():
        prompt += f"""
    {date}:
    - Nhiệt độ: {stats[('Nhiệt độ (°C)', 'min')]}°C - {stats[('Nhiệt độ (°C)', 'max')]}°C (TB: {stats[('Nhiệt độ (°C)', 'mean')]}°C)
    - Độ ẩm TB: {stats[('Độ ẩm (%)', 'mean')]}%
    - Áp suất TB: {stats[('Áp suất (hPa)', 'mean')]} hPa
    - Tốc độ gió TB: {stats[('Tốc độ gió (m/s)', 'mean')]} m/s
    - Mây TB: {stats[('Mây (%)', 'mean')]}%
    - Tổng lượng mưa: {stats[('Lượng mưa (mm)', 'sum')]} mm
    """
    
    # Thêm phân tích xu hướng
    trends = {
        'temp_trend': df['Nhiệt độ (°C)'].diff().mean(),
        'humidity_trend': df['Độ ẩm (%)'].diff().mean(),
        'pressure_trend': df['Áp suất (hPa)'].diff().mean(),
        'wind_trend': df['Tốc độ gió (m/s)'].diff().mean(),
    }
    
    prompt += f"""
    Xu hướng biến đổi:
    - Nhiệt độ: {'tăng' if trends['temp_trend'] > 0 else 'giảm'} ({abs(trends['temp_trend']):.2f}°C/3h)
    - Độ ẩm: {'tăng' if trends['humidity_trend'] > 0 else 'giảm'} ({abs(trends['humidity_trend']):.2f}%/3h)
    - Áp suất: {'tăng' if trends['pressure_trend'] > 0 else 'giảm'} ({abs(trends['pressure_trend']):.2f}hPa/3h)
    - Gió: {'mạnh lên' if trends['wind_trend'] > 0 else 'yếu đi'} ({abs(trends['wind_trend']):.2f}m/s/3h)
    
    Dựa trên xu hướng biến đổi trên, hãy phân tích thêm về khả năng thay đổi thời tiết trong các ngày tới.
    """
    
    prompt += """
    Hãy phân tích và đưa ra:
    1. Nhận định về điều kiện thời tiết hiện tại
    2. Dự báo chi tiết cho từng ngày trong 5 ngày tới
    3. Xu hướng thời tiết tổng quan trong 5 ngày
    4. Các cảnh báo và khuyến nghị cho người dân (nếu có)
    
    Hãy trình bày phân tích một cách chuyên nghiệp và dễ hiểu.
    """
    
    chat = model.start_chat(history=[])
    response = chat.send_message(prompt)
    return response.text

def main():
    st.title("Ứng dụng Dự báo Thời tiết A Lưới")
    
    # Tọa độ của A Lưới
    lat = 16.2333
    lon = 107.2833
    
    try:
        # Lấy dữ liệu thời tiết
        weather_data = get_weather_data(lat, lon)
        df = analyze_weather_data(weather_data)
        
        # Tạo tabs - thêm tab3 cho Thiết bị giám sát
        tab1, tab2, tab3 = st.tabs(["Dữ liệu thời tiết", "Phân tích & Dự báo", "Thiết bị giám sát"])
        
        with tab1:
            st.subheader("Bảng dữ liệu thời tiết")
            
            # Thêm bộ lọc theo ngày
            df['Date'] = pd.to_datetime(df['Thời gian']).dt.date
            selected_date = st.selectbox('Chọn ngày:', options=df['Date'].unique())
            filtered_df = df[df['Date'] == selected_date]
            st.dataframe(filtered_df)
            
            # Vẽ các biểu đồ
            st.subheader("Biểu đồ các thông số thời tiết")
            
            # Biểu đồ nhiệt độ cho tất cả các ngày
            st.subheader("Xu hướng nhiệt độ trong 5 ngày")
            st.line_chart(df.set_index('Thời gian')[['Nhiệt độ (°C)', 'Nhiệt độ min (°C)', 'Nhiệt độ max (°C)']])
            
            # Biểu đồ cho ngày được chọn
            st.subheader(f"Biểu đồ chi tiết ngày {selected_date}")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("Độ ẩm (%)")
                st.line_chart(filtered_df.set_index('Thời gian')['Độ ẩm (%)'])
            with col2:
                st.caption("Áp suất (hPa)")
                st.line_chart(filtered_df.set_index('Thời gian')['Áp suất (hPa)'])
            
            col3, col4 = st.columns(2)
            with col3:
                st.caption("Tốc độ gió (m/s)")
                st.line_chart(filtered_df.set_index('Thời gian')['Tốc độ gió (m/s)'])
            with col4:
                st.caption("Mây (%)")
                st.line_chart(filtered_df.set_index('Thời gian')['Mây (%)'])
        
        with tab2:
            st.subheader("Phân tích và Dự báo Thời tiết")
            
            if st.button("Phân tích dữ liệu"):
                with st.spinner("Đang phân tích dữ liệu..."):
                    analysis = get_ai_analysis(df)
                    st.markdown(analysis)
                    
        with tab3:
            ngrok_url = "https://943f-27-78-22-92.ngrok-free.app"

            try:
                headers = {
                    'ngrok-skip-browser-warning': 'true',
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                response = requests.get(ngrok_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    components.html(
                        f'''
                        <iframe 
                            src="{ngrok_url}?ngrok-skip-browser-warning=true"
                            width="100%"
                            style="border: none;"
                            allow="autoplay; fullscreen; picture-in-picture"
                            allowfullscreen
                            sandbox="allow-forms allow-scripts allow-same-origin"
                        ></iframe>
                        ''',
                        height=600,
                        scrolling=True
                    )
                else:
                    st.error("Không thể kết nối đến thiết bị")
            except requests.Timeout:
                st.error("Kết nối bị timeout")
            except Exception as e:
                st.error(f"Lỗi kết nối: {str(e)}")

    except Exception as e:
        st.error(f"Có lỗi xảy ra: {str(e)}")

if __name__ == "__main__":
    main()
