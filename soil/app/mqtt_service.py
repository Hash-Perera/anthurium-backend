
import json
import os
import paho.mqtt.client as mqtt
from pymongo import MongoClient
from datetime import datetime
import random
from dotenv import load_dotenv

# Load Env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://dbuser:dbuser@geosoil.vmlcqs8.mongodb.net")
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "geosoil/sensor_data"

# Setup Sync Mongo Client for this thread
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_database("test") # Matches database.py
collection = db.sensordatas

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected to {MQTT_BROKER}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[MQTT] Failed to connect, rc={rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        # Overwrite with simulated healthy values
        data['n'] = random.randint(40, 60)
        data['p'] = random.randint(15, 30)
        data['k'] = random.randint(50, 80)

        print(f"[MQTT] Received: {data}")

        # Map data
        # JSON keys from ESP32: lat, lon, temp, hum, soil_raw, n, p, k
        
        t = data.get("temp", 0)
        t = float(t) if t is not None else 0.0

        h = data.get("hum", 0)
        h = float(h) if h is not None else 0.0
        
        sm_raw = data.get("soil_raw", 0)
        sm_raw = float(sm_raw) if sm_raw is not None else 0.0

        # Calibration: 
        # ESP32 ADC is 12-bit (0-4095). 
        # Typically Capacitive/Resistive Sensors:
        #   Air (Dry) = High Value (~3000-4095) -> 0%
        #   Water (Wet) = Low Value (~0-1000) -> 100%
        # Simple Inverted Mapping:
        soil_pct = ((4095 - sm_raw) / 4095.0) * 100
        soil_pct = max(0.0, min(100.0, soil_pct)) # Clamp 0-100

        # Calculate Health
        # 20 <= T <= 30 AND H >= 60 AND Soil >= 40%
        is_healthy = (20 <= t <= 30) and (h >= 60) and (soil_pct >= 40)

        new_reading = {
            "location": {
                "type": "Point",
                "coordinates": [data.get("lon", 0), data.get("lat", 0)]
            },
            "soilMoisture": round(soil_pct, 1), # Save percentage
            "humidity": h,
            "temperature": t,
            "nitrogen": data.get("n", 0),
            "phosphorus": data.get("p", 0),
            "potassium": data.get("k", 0),
            "isHealthy": is_healthy,
            "timestamp": datetime.now()
        }

        collection.insert_one(new_reading)
        print("[MQTT] Saved to MongoDB")

    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")

def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"[MQTT] Connecting to {MQTT_BROKER}...")
    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.loop_start() # Runs in background thread
    except Exception as e:
        print(f"[MQTT] Connection failed: {e}")
