import requests
import logging
import os
from datetime import datetime


logger = logging.getLogger("weather")

class WeatherService:
    def __init__(self):
        # ВСТАВ СЮДИ СВІЙ API KEY
        self.api_key = os.getenv("OPENWEATHER_API_KEY")  
        
        self.default_city = "Boyarka" 
        self.lang = "ua"

    def get_weather(self, city_name=None) -> str:
        """Поточна погода"""
        city = city_name if city_name else self.default_city
        url = (f"https://api.openweathermap.org/data/2.5/weather?"
               f"q={city}&appid={self.api_key}&units=metric&lang={self.lang}")
        try:
            r = requests.get(url, timeout=5).json()
            if r.get("cod") != 200: return f"Помилка: {r.get('message')}"
            
            temp = round(r['main']['temp'])
            desc = r['weather'][0]['description']
            return f"У місті {city} зараз {desc}, {temp}°C."
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return "Не вдалося отримати поточну погоду."

    def get_forecast(self, city_name=None) -> str:
        """Прогноз на найближчі 12 годин (крок 3 години)"""
        city = city_name if city_name else self.default_city
        
        # Використовуємо endpoint /forecast (він безкоштовний)
        url = (f"https://api.openweathermap.org/data/2.5/forecast?"
               f"q={city}&appid={self.api_key}&units=metric&lang={self.lang}")

        try:
            r = requests.get(url, timeout=5).json()
            if r.get("cod") != "200": return f"Помилка прогнозу: {r.get('message')}"

            forecast_list = r['list']
            report = [f"Прогноз для {city} на найближчий час:"]

            # Беремо перші 4 записи (4 * 3 години = 12 годин вперед)
            for item in forecast_list[:4]:
                # item['dt_txt'] має вигляд "2023-10-27 15:00:00"
                dt_obj = datetime.strptime(item['dt_txt'], "%Y-%m-%d %H:%M:%S")
                time_str = dt_obj.strftime("%H:%M") # Отримуємо "15:00"
                
                temp = round(item['main']['temp'])
                desc = item['weather'][0]['description']
                
                # Додаємо рядок типу: "О 15:00 — дощ, 12 градусів."
                report.append(f"О {time_str} — {desc}, {temp}°.")

            return "\n".join(report)

        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return "Не вдалося отримати прогноз."

weather = WeatherService()