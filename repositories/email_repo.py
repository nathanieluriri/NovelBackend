from core.database import db
from schemas.email_schema import ClientData
from bson import ObjectId,errors
import asyncio


async def create_email_log(client_data: ClientData):
    print(client_data)
    
    result = await db.LoginAttempts.insert_one(client_data)
    created_log = await db.LoginAttempts.find_one({"_id": result.inserted_id})
    return created_log

