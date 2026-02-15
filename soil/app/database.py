import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Try loading from current dir, then parent
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://dbuser:dbuser@geosoil.vmlcqs8.mongodb.net/test")

client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database("test")
