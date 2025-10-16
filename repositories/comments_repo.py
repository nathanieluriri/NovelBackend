
from core.database import db
from schemas.comments_schema import CommentOut,CommentCreate
from bson import ObjectId,errors
import asyncio

async def get_all_user_comments(userId):
    cursor= db.comments.find({"userId":userId})
    retrieved_comments= [chapters async for chapters in cursor]
    return retrieved_comments


async def get_all_chapter_comments(chapterId):
    cursor= db.comments.find({"chapterId":chapterId})
    retrieved_comments= [chapters async for chapters in cursor]
    return retrieved_comments


async def delete_comments_with_chapter_id(chapterId: list):
    """_summary_
    
    Accepts a list of page Id's and deletes comments with it
    
    Args:
        chapterId (list): _description_

    Returns:
        _type_: _description_
    """
    result = await db.comments.delete_many({"chapterId": {"$in": chapterId}})
    return result

async def delete_comments_with_user_id(userId: list):
    """_summary_
    Accepts list of user Id's and deletes comments with it
    Args:
        userId (list): _description_
        

    Returns:
        _type_: _description_
    """
    result = await db.comments.delete_many({"userId": {"$in": userId}})
    return result


async def create_comment(comment_data: CommentCreate):
    comment = comment_data.model_dump()
    print(comment)
    result = await db.comments.insert_one(comment)
    created_comment = await db.comments.find_one({"_id": result.inserted_id})
    return created_comment



async def delete_comment_with_comment_id(commentId: str):
    try:
        obj_id = ObjectId(commentId)
    except errors.InvalidId:
        return None  # or raise an error / log it
    return await db.comments.find_one_and_delete({"_id": obj_id})


async def update_comment_with_comment_id(commentId: str, userId: str, text: str):
    try:
        obj_id = ObjectId(commentId)
    except errors.InvalidId:
        return None  # You might also want to log this

    result = await db.comments.update_one(
        {"_id": obj_id, "userId": userId},
        {"$set": {"text": text}}
    )
    data = await db.comments.find_one(filter={"_id":obj_id})
    return data


async def delete_comment_with_comment_id_userId(userId,commentId: str):
    try:
        obj_id = ObjectId(commentId)
    except errors.InvalidId:
        return None  # or raise an error / log it
    return await db.comments.find_one_and_delete({"_id": obj_id,"userId":userId})



