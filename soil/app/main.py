from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router as api_router
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    from .mqtt_service import start_mqtt
    start_mqtt()

@app.get("/")
async def root():
    return {"message": "GeoSoil Python Backend Running (MQTT Enabled)"}
