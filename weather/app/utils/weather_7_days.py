import requests
import os
from collections import defaultdict
from datetime import datetime

API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_7_day_weather(city: str):
    query_city = city if "," in city else f"{city},LK"
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": query_city,
        "appid": API_KEY,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    daily = defaultdict(list)

    for item in data["list"]:
        date = datetime.fromtimestamp(item["dt"]).date()
        daily[date].append(item)

    forecast = []
    for date, entries in list(daily.items())[:7]:
        temps = [e["main"]["temp"] for e in entries]

        forecast.append({
            "date": str(date),
            "temp_min": min(temps),
            "temp_max": max(temps),
            "humidity": sum(e["main"]["humidity"] for e in entries) // len(entries),
            "weather": entries[0]["weather"][0]["description"],
            "wind_speed": entries[0]["wind"]["speed"]
        })

    return forecast
