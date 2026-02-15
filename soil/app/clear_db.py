
import asyncio
from database import db

async def clear_db():
    print("Clearing 'sensordatas' collection...")
    result = await db.sensordatas.delete_many({})
    print(f"Deleted {result.deleted_count} documents.")

if __name__ == "__main__":
    asyncio.run(clear_db())
