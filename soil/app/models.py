from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Location(BaseModel):
    type: str = "Point"
    coordinates: List[float] # [longitude, latitude]

class SensorDataCreate(BaseModel):
    lat: float
    lng: float
    soilMoisture: Optional[float] = None
    humidity: Optional[float] = None
    temperature: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    isHealthy: bool = True

class SensorData(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.now)
    location: Location
    soilMoisture: Optional[float] = None
    humidity: Optional[float] = None
    temperature: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    isHealthy: bool

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
