import os
from collections import defaultdict
from datetime import datetime

import requests


API_KEY = os.getenv("OPENWEATHER_API_KEY")


def get_3_day_recommendation(city: str):
    """
    Pull a 3-day forecast from OpenWeather and return care recommendations.
    """

    query_city = city if "," in city else f"{city},LK"
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": query_city,
        "appid": API_KEY,
        "units": "metric",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    daily = defaultdict(list)
    for item in data["list"]:
        date = datetime.fromtimestamp(item["dt"]).date()
        daily[date].append(item)

    forecast = []
    for date, entries in list(daily.items())[:3]:
        temps = [e["main"]["temp"] for e in entries]
        humidity = sum(e["main"]["humidity"] for e in entries) / len(entries)
        rainfall = 0.0
        for entry in entries:
            rain = entry.get("rain", {})
            rainfall += float(rain.get("3h", 0.0) or rain.get("1h", 0.0))

        forecast.append({
            "date": str(date),
            "temp": sum(temps) / len(temps),
            "humidity": humidity,
            "rainfall": rainfall,
        })

    # --- Average calculations ---
    avg_temp = sum(day["temp"] for day in forecast) / 3
    avg_humidity = sum(day["humidity"] for day in forecast) / 3
    avg_rainfall = sum(day["rainfall"] for day in forecast) / 3

    # --- Condition checks ---
    rainy_condition = (
        avg_rainfall >= 35 and
        avg_humidity >= 80
    )

    sunny_condition = (
        avg_rainfall <= 20 and
        avg_temp >= 30 and
        avg_humidity <= 70
    )

    # --- Recommendations (NO WATERING) ---
    if rainy_condition:
        return {
            "weather_type": "Rainy",
            "avg_temp": round(avg_temp, 1),
            "avg_humidity": round(avg_humidity, 1),
            "avg_rainfall": round(avg_rainfall, 1),
            "recommendations": [
                "Ensure proper drainage to avoid waterlogging around roots.",
                "Increase air circulation to reduce fungal and bacterial diseases."
            ]
        }

    elif sunny_condition:
        return {
            "weather_type": "Sunny",
            "avg_temp": round(avg_temp, 1),
            "avg_humidity": round(avg_humidity, 1),
            "avg_rainfall": round(avg_rainfall, 1),
            "recommendations": [
                "Use 50–70% shade net to protect plants from direct sunlight.",
                "Apply mulching to maintain root-zone temperature and moisture."
            ]
        }

    else:
        return {
            "weather_type": "Normal",
            "avg_temp": round(avg_temp, 1),
            "avg_humidity": round(avg_humidity, 1),
            "avg_rainfall": round(avg_rainfall, 1),
            "recommendations": [
                "Maintain suitable shade and ventilation conditions.",
                "Regularly inspect plants for pests and diseases."
            ]
        }