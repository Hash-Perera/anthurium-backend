import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def list_dbs():
    # Connect to the cluster root (ignore the db in uri for a moment if possible, or just use client)
    uri = os.getenv("MONGO_URI")
    # We want to connect to the cluster to list dbs
    client = AsyncIOMotorClient(uri)
    
    print("Databases on server:")
    dbs = await client.list_database_names()
    print(dbs)

    # Check 'test' database specifically as it is a common default
    if 'test' in dbs:
        db = client.get_database('test')
        cols = await db.list_collection_names()
        print(f"Collections in 'test': {cols}")
        for col in cols:
             count = await db[col].count_documents({})
             print(f"  {col}: {count}")

    # Check if 'geo_soil_db' exists
    if 'geo_soil_db' in dbs:
         db = client.get_database('geo_soil_db')
         cols = await db.list_collection_names()
         print(f"Collections in 'geo_soil_db': {cols}")

if __name__ == "__main__":
    asyncio.run(list_dbs())
