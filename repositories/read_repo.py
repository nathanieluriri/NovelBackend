from core.database import db
from schemas.read_schema import MarkAsRead
from bson import ObjectId,errors
from pymongo import ASCENDING
from datetime import datetime, timezone

async def get_all_chapters_user_has_read(userId):
    cursor= db.read.find({"userId":userId})
    retrieved_chapters= [chapters async for chapters in cursor]
    return retrieved_chapters


async def get_particular_chapter_user_has_read(userId:str,chapterId:str)->MarkAsRead:
    result= await db.read.find_one({"userId":userId,"chapterId":chapterId})
    if result:
        return MarkAsRead(**result)
    return MarkAsRead(userId=userId,chapterId=chapterId,hasRead=False)

async def upsert_read_record(data:MarkAsRead):
    index_keys = [
        ("userId", ASCENDING),
        ("chapterId", ASCENDING)
    ]
    collection = db.read
    try:
        # Create the index. It's idempotent, so safe to call multiple times.
        await collection.create_index(index_keys, unique=True, background=True)
        print(f"Unique compound index on 'userId' and 'chapterId' ensured for '{collection.name}' collection.")
    except Exception as e:
        print(f"Error ensuring index for '{collection.name}': {e}")
    query = {
        "userId": data.userId,
        "chapterId": data.chapterId
    }

    # The update operation using $set for partial updates,
    # and $currentDate/$setOnInsert for timestamps.
    update_operation = {
        "$set": data, # This contains the fields you want to update/set
        "$currentDate": {"lastUpdated": True}, # Update 'lastUpdated' timestamp on every operation
        "$setOnInsert": {"dateCreated": datetime.now(timezone.utc).isoformat()} # Set 'dateCreated' only on insert
    }

    try:
        result = await collection.update_one(
            query,
            update_operation,
            upsert=True # Crucial: insert if not found, update if found
        )


    except Exception as e:
        print(f"Error during upsert operation for userId: {data.userId}, chapterId: {data.chapterId}: {e}")
        raise