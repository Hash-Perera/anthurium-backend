from fastapi import APIRouter, HTTPException, Body
from typing import List
from .database import db
from .models import SensorData, SensorDataCreate, Location, SoilConditions
from .utils.recomndations import generate_anthurium_recommendations, get_required_conditions

from datetime import datetime

router = APIRouter()

@router.get("/readings", response_model=List[SensorData])
async def get_readings():
    readings = await db.sensordatas.find().sort("timestamp", -1).to_list(1000)
    # Convert _id to string manually if needed, or rely on pydantic alias
    # Motor returns _id as ObjectId, Pydantic needs string or ObjectId handling
    # For simplicity, we can map it.
    results = []
    print(f"Fetched {len(readings)} readings")
    for r in readings:
        print(f"Reading: {r}")
        r["_id"] = str(r["_id"])
        results.append(r)
    return results

@router.post("/readings", status_code=201)
async def create_reading(reading: SensorDataCreate):
    # Logic from Node backend:
    # const isHealthy = (
    #     temperature >= 20 && temperature <= 30 &&
    #     humidity >= 60 &&
    #     soilMoisture >= 40
    # );
    
    # We use the values passed in, assuming they match the schema
    # But we need to calculate 'isHealthy' if not explicitly passed (Node logic calculated it)
    # The Node logic ignored the 'isHealthy' from body (it wasn't in req.body destructuring for logic, but was in destructuring?)
    # Wait, Node code: const { isHealthy } = req.body (NO, it calculated it)
    # Ah, reading the Node code again:
    # `const { lat, lng, soilMoisture, humidity, temperature, ... } = req.body`
    # `const isHealthy = ...`
    # `const reading = new SensorData({ ... isHealthy })`
    # So the client sends raw data, server calculates health.

    t = reading.temperature or 0
    h = reading.humidity or 0
    sm = reading.soilMoisture or 0

    calculated_is_healthy = (
        20 <= t <= 30 and
        h >= 60 and
        sm >= 40
    )

    new_reading = {
        "location": {
            "type": "Point",
            "coordinates": [reading.lng, reading.lat]
        },
        "soilMoisture": reading.soilMoisture,
        "humidity": reading.humidity,
        "temperature": reading.temperature,
        "nitrogen": reading.nitrogen,
        "phosphorus": reading.phosphorus,
        "potassium": reading.potassium,
        "isHealthy": calculated_is_healthy,
        "timestamp": datetime.now()
    }

    result = await db.sensordatas.insert_one(new_reading)
    new_reading["_id"] = str(result.inserted_id)
    return new_reading

# Get latest sensor data record
@router.get("/readings/latest", response_model=SensorData)
async def get_latest_reading():
    latest = await db.sensordatas.find_one(sort=[("timestamp", -1)])
    if not latest:
        raise HTTPException(status_code=404, detail="No sensor data found")
    latest["_id"] = str(latest["_id"])
    return latest

@router.post("/readings/recommendations", response_model=dict)
async def get_recommendations(current_conditions: SoilConditions, flower: str = "Anthurium"):
    # Convert Pydantic model to dict
    current_dict = current_conditions.model_dump(exclude_none=False)
    
    # Get required conditions for the specified flower variety
    required_conditions = get_required_conditions(flower.lower())
    
    # Generate AI recommendations
    return generate_anthurium_recommendations(current_dict, required_conditions, flower)
