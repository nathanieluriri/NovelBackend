from core.database import db
from schemas.user_schema import NewUserCreate,NewUserOut
from bson import ObjectId

async def get_user_by_email(email: str):
    return await db.users.find_one({"email": email})

async def create_user(user_data: NewUserCreate):
    user = user_data.model_dump()
    result = await db.users.insert_one(user)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    return created_user


async def get_user_by_email_and_provider(email: str,provider:str):
    return await db.users.find_one({"email": email,"provider":provider})


async def get_user_by_userId(userId: str):
    return await db.users.find_one({"_id": ObjectId(userId)})

async def replace_password(userId: str, hashedPassword: str):
    await db.users.find_one_and_update(
        filter={"_id": ObjectId(userId)},
        update={"$set": {"password": hashedPassword}}
    )
    