
from core.database import db
from schemas.bookmark_schema import BookMarkOut,BookMarkCreate
from bson import ObjectId,errors
import asyncio

async def get_all_user_bookmarks(userId):
    cursor= db.bookmarks.find({"userId":userId})
    retrieved_bookmarks= [chapters async for chapters in cursor]
    return retrieved_bookmarks


async def delete_bookmarks_with_page_id(pageId: list):
    """_summary_
    
    Accepts a list of page Id's and deletes bookmarks with it
    
    Args:
        pageId (list): _description_

    Returns:
        _type_: _description_
    """
    result = await db.bookmarks.delete_many({"pageId": {"$in": pageId}})
    return result

async def delete_bookmarks_with_user_id(userId: list):
    """_summary_
    Accepts list of user Id's and deletes bookmarks with it
    Args:
        userId (list): _description_
        

    Returns:
        _type_: _description_
    """
    result = await db.bookmarks.delete_many({"userId": {"$in": userId}})
    return result


async def create_bookmark(bookmark_data: BookMarkCreate):
    bookmark = bookmark_data.model_dump()
    result = await db.bookmarks.insert_one(bookmark)
    created_like = await db.bookmarks.find_one({"_id": result.inserted_id})
    return created_like



async def delete_bookmarks_with_bookmark_id(bookmarkId: str):
    try:
        obj_id = ObjectId(bookmarkId)
    except errors.InvalidId:
        return None  # or raise an error / log it
    return await db.bookmarks.find_one_and_delete({"_id": obj_id})



