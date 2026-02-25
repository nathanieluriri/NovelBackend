from core.database import db
from schemas.user_schema import NewUserCreate,UserOut
from bson import ObjectId
from typing import List

async def get_user_by_email(email: str):
    return await db.users.find_one({"email": email})

async def checks_user_balance(userId:str):
    try:
        user = await db.users.find_one({"_id":ObjectId(userId)})
        if user:
            userOut = UserOut(**user)
            return userOut.balance
        else: return None
    except:
        return None
    
async def subtract_from_user_balance(userId,number_of_stars):
    try:
        user = await db.users.find_one({"_id":ObjectId(userId)})
        if user:
            userOut = UserOut(**user)
            await db.users.update_one(
                filter={"_id":ObjectId(userOut.userId)},
                update={"$set":{"balance":(userOut.balance-number_of_stars)}}
            )
        else: return None
    except:
        return None
    
    
async def add_to_user_balance(userId,number_of_stars):
    try:
        user = await db.users.find_one({"_id":ObjectId(userId)})
        if user:
            userOut = UserOut(**user)
            await db.users.update_one(
                filter={"_id":ObjectId(userOut.userId)},
                update={"$set":{"balance":(userOut.balance+number_of_stars)}}
            )
        else: return None
    except:
        return None
    
async def update_user_unlocked_chapters(userId,chapterId):
    try:
        user = await db.users.find_one({"_id":ObjectId(userId)})
        if user:
            userOut = UserOut(**user)
            oldlist = userOut.unlockedChapters
            for items in oldlist:
                if items==chapterId:
                    return None
            oldlist.append(chapterId)
            print("new List",oldlist)
            await db.users.update_one(
                filter={"_id":ObjectId(userOut.userId)},
                update={"$set":{"unlockedChapters":oldlist}}
            )
            return True
        else: return None
    except:
        return None


async def update_user_subscription(userId: str, subscription: dict):
    try:
        user = await db.users.find_one({"_id": ObjectId(userId)})
        if not user:
            return None
        await db.users.update_one(
            filter={"_id": ObjectId(userId)},
            update={"$set": {"subscription": subscription}},
        )
        return True
    except:
        return None
    

async def get_all_users():
    user_cursor = db.users.find()
    users = await user_cursor.to_list(length=None)
    return users

async def create_user(user_data: NewUserCreate):
    user = user_data.model_dump()
    result = await db.users.insert_one(user)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    return created_user


async def get_user_by_email_and_provider(email: str,provider:str):
    return await db.users.find_one({"email": email,"provider":provider})


async def get_user_by_userId(userId: str):
    return await db.users.find_one({"_id": ObjectId(userId)})


async def get_users_by_user_ids(userIds: List[str]):
    object_ids = []
    for user_id in userIds:
        if ObjectId.is_valid(user_id):
            object_ids.append(ObjectId(user_id))

    if not object_ids:
        return []

    cursor = db.users.find({"_id": {"$in": object_ids}})
    return await cursor.to_list(length=None)

async def replace_password(userId: str, hashedPassword: str):
    await db.users.find_one_and_update(
        filter={"_id": ObjectId(userId)},
        update={"$set": {"password": hashedPassword}}
    )
    
    
async def update_user_profile(userId: str, update: dict):
    updated_doc = await db.users.find_one_and_update(
        filter={"_id": ObjectId(userId)},
        update={"$set": update},
        return_document=True  # or ReturnDocument.AFTER if using pymongo
    )
    return updated_doc
