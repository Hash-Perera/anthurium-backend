import requests
import os

API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_today_weather(city: str):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Temperature (°C)
    temperature_c = data["main"]["temp"]

    # Humidity (%)
    humidity_pct = data["main"]["humidity"]

    # Rainfall (mm) - OpenWeather may omit this
    rainfall_mm = 0.0
    if "rain" in data:
        rainfall_mm = data["rain"].get("1h", 0.0) or data["rain"].get("3h", 0.0)

    # Wind speed (km/h) → OpenWeather gives m/s
    wind_kmph = data["wind"]["speed"] * 3.6

    return {
        "temperature_c": round(temperature_c, 2),
        "humidity_pct": round(humidity_pct, 2),
        "rainfall_mm": round(rainfall_mm, 2),
        "wind_kmph": round(wind_kmph, 2)
    }
