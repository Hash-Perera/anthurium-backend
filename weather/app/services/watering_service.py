import pandas as pd
import joblib
from pathlib import Path

# ---------------------------
# Load model & encoders ONCE
# ---------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

model = joblib.load(BASE_DIR / "models" / "watering_model.pkl")
district_encoder = joblib.load(BASE_DIR / "models" / "district_encoder.pkl")
watering_encoder = joblib.load(BASE_DIR / "models" / "watering_encoder.pkl")

# ---------------------------
# Watering policy mapping
# ---------------------------

WATERING_POLICY = {
    "Low": {
        "watering_frequency_per_day": 1,
        "watering_time": "07:00",
        "water_amount": "300ml"
    },
    "Moderate": {
        "watering_frequency_per_day": 1,
        "watering_time": "07:00",
        "water_amount": "500ml"
    },
    "High": {
        "watering_frequency_per_day": 2,
        "watering_time": "07:00 & 17:30",
        "water_amount": "400ml + 300ml"
    },
    "Very High": {
        "watering_frequency_per_day": 2,
        "watering_time": "06:30 & 18:00",
        "water_amount": "600ml + 400ml"
    }
}

# ---------------------------
# Prediction function
# ---------------------------

def predict_watering_plan(
    district: str,
    temperature_c: float,
    humidity_pct: float,
    rainfall_mm: float,
    wind_kmph: float
):
    district_encoded = district_encoder.transform([district])[0]

    input_df = pd.DataFrame([{
        "district": district_encoded,
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "rainfall_mm": rainfall_mm,
        "wind_kmph": wind_kmph
    }])

    predicted_label = model.predict(input_df)[0]
    watering_level = watering_encoder.inverse_transform([predicted_label])[0]

    policy = WATERING_POLICY[watering_level]

    return {
        "watering_level": watering_level,
        "watering_frequency_per_day": policy["watering_frequency_per_day"],
        "watering_time": policy["watering_time"],
        "water_amount": policy["water_amount"]
    }
