from core.database import db
from schemas.likes_schema import LikeOut,LikeCreate
from bson import ObjectId,errors
import asyncio

async def get_all_user_likes(userId, skip: int = 0, limit: int | None = None):
    cursor = db.likes.find({"userId": userId}).skip(skip)
    if limit is not None:
        cursor = cursor.limit(limit)
    retrieved_likes= [chapters async for chapters in cursor]
    return retrieved_likes


async def count_user_likes(userId: str) -> int:
    return await db.likes.count_documents({"userId": userId})


async def get_all_chapter_likes(chapterId):
    cursor= db.likes.find({"chapterId":chapterId})
    retrieved_likes= [chapters async for chapters in cursor]
    return retrieved_likes


async def delete_likes_with_page_id(chapterId: list):
    """_summary_
    
    Accepts a list of page Id's and deletes likes with it
    
    Args:
        chapterId (list): _description_

    Returns:
        _type_: _description_
    """
    result = await db.likes.delete_many({"chapterId": {"$in": chapterId}})
    return result

async def delete_likes_with_user_id(userId: list):
    """_summary_
    Accepts list of user Id's and deletes likes with it
    Args:
        userId (list): _description_
        

    Returns:
        _type_: _description_
    """
    result = await db.likes.delete_many({"userId": {"$in": userId}})
    return result


async def create_like(like_data: LikeCreate):
    like = like_data.model_dump()
    already_liked = await db.likes.find_one(filter={"userId":like_data.userId,"chapterId":like_data.chapterId})
    if already_liked==None:
        result = await db.likes.insert_one(like)
        created_like = await db.likes.find_one({"_id": result.inserted_id})
        return created_like
    else:return already_liked



async def delete_like_with_like_id(likeId: str):
    try:
        obj_id = ObjectId(likeId)
    except errors.InvalidId:
        return None  # or raise an error / log it
    return await db.likes.find_one_and_delete({"_id": obj_id})


