from core.database import db
from schemas.likes_schema import LikeOut,LikeCreate
from bson import ObjectId,errors
import asyncio

async def get_all_user_likes(userId):
    cursor= db.likes.find({"userId":userId})
    retrieved_likes= [chapters async for chapters in cursor]
    return retrieved_likes


async def delete_likes_with_page_id(pageId: list):
    """_summary_
    
    Accepts a list of page Id's and deletes likes with it
    
    Args:
        pageId (list): _description_

    Returns:
        _type_: _description_
    """
    result = await db.likes.delete_many({"pageId": {"$in": pageId}})
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
    result = await db.likes.insert_one(like)
    created_like = await db.likes.find_one({"_id": result.inserted_id})
    return created_like



async def delete_like_with_like_id(likeId: str):
    try:
        obj_id = ObjectId(likeId)
    except errors.InvalidId:
        return None  # or raise an error / log it
    return await db.likes.find_one_and_delete({"_id": obj_id})


