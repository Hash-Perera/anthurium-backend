from enum import Enum

from fastapi import FastAPI, HTTPException
from app.utils.weather_7_days import get_7_day_weather
from app.services.watering_service import predict_watering_plan
from app.services.weather_today import get_today_weather
from app.utils.three_day_weather_recomdation import get_3_day_recommendation



app = FastAPI(
    title="Weather detection and watering time suggestion",
    description="A FastAPI application for Weather detection and watering time suggestion",
    version="1.0.0"
)



@app.get("/")
def read_root():
    return {"message": "Weather detection and watering time suggestion up and running"}

class District(str, Enum):
    ampara = "Ampara"
    anuradhapura = "Anuradhapura"
    badulla = "Badulla"
    batticaloa = "Batticaloa"
    colombo = "Colombo"
    galle = "Galle"
    gampaha = "Gampaha"
    hambantota = "Hambantota"
    jaffna = "Jaffna"
    kalutara = "Kalutara"
    kandy = "Kandy"
    kegalle = "Kegalle"
    kilinochchi = "Kilinochchi"
    kurunegala = "Kurunegala"
    mannar = "Mannar"
    matale = "Matale"
    matara = "Matara"
    monaragala = "Monaragala"
    nuwara_eliya = "Nuwara Eliya"
    polonnaruwa = "Polonnaruwa"
    puttalam = "Puttalam"
    ratnapura = "Ratnapura"
    trincomalee = "Trincomalee"
    vavuniya = "Vavuniya"

@app.get("/weather/7-day")
def weather_7_day(city: District):
    return get_7_day_weather(city.value)

@app.get("/watering/recommendation")
def get_watering_recommendation(city: District):
    try:
        # 1. Fetch today's weather
        weather = get_today_weather(city.value)

        # 2. Run ML + rule engine
        result = predict_watering_plan(
            district=city.value,
            temperature_c=weather["temperature_c"],
            humidity_pct=weather["humidity_pct"],
            rainfall_mm=weather["rainfall_mm"],
            wind_kmph=weather["wind_kmph"]
        )

        return {
            "city": city.value,
            "weather": weather,
            **result
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate watering recommendation"
        )


@app.get("/weather/3-day-recommendation")
def weather_3_day_recommendation_endpoint(city: District):
    return get_3_day_recommendation(city.value)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
