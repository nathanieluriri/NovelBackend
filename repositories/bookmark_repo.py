from bson import ObjectId, errors
from pymongo import ASCENDING, DESCENDING

from core.database import db
from schemas.bookmark_schema import BookMarkCreate, InteractionTargetType


async def ensure_bookmark_indexes():
    await db.bookmarks.create_index(
        [("userId", ASCENDING), ("targetType", ASCENDING), ("targetId", ASCENDING)],
        unique=True,
        partialFilterExpression={"targetType": {"$exists": True}, "targetId": {"$exists": True}},
        background=True,
    )
    await db.bookmarks.create_index(
        [("userId", ASCENDING), ("dateCreated", DESCENDING)],
        background=True,
    )


async def get_all_user_bookmarks(
    userId: str,
    targetType: InteractionTargetType | None = None,
    skip: int = 0,
    limit: int = 20,
):
    await ensure_bookmark_indexes()
    query = {"userId": userId}
    if targetType is not None:
        query["targetType"] = targetType.value
    cursor = db.bookmarks.find(query).skip(skip).limit(limit)
    return [bookmark async for bookmark in cursor]


async def count_user_bookmarks(
    userId: str,
    targetType: InteractionTargetType | None = None,
) -> int:
    query = {"userId": userId}
    if targetType is not None:
        query["targetType"] = targetType.value
    return await db.bookmarks.count_documents(query)


async def get_bookmark_by_user_target(userId: str, targetType: InteractionTargetType, targetId: str):
    await ensure_bookmark_indexes()
    return await db.bookmarks.find_one(
        {"userId": userId, "targetType": targetType.value, "targetId": targetId}
    )


async def delete_bookmarks_with_page_id(pageIds: list):
    return await db.bookmarks.delete_many(
        {
            "$or": [
                {"pageId": {"$in": pageIds}},
                {"targetType": InteractionTargetType.page.value, "targetId": {"$in": pageIds}},
            ]
        }
    )


async def delete_bookmarks_with_user_id(userIds: list):
    return await db.bookmarks.delete_many({"userId": {"$in": userIds}})


async def create_bookmark(bookmark_data: BookMarkCreate):
    await ensure_bookmark_indexes()
    bookmark = bookmark_data.model_dump()
    result = await db.bookmarks.insert_one(bookmark)
    return await db.bookmarks.find_one({"_id": result.inserted_id})


async def delete_bookmarks_with_bookmark_id(bookmarkId: str):
    try:
        obj_id = ObjectId(bookmarkId)
    except errors.InvalidId:
        return None
    return await db.bookmarks.find_one_and_delete({"_id": obj_id})


async def delete_bookmark_by_id_userId(bookmarkId: str, userId: str):
    try:
        obj_id = ObjectId(bookmarkId)
    except errors.InvalidId:
        return None
    return await db.bookmarks.find_one_and_delete({"_id": obj_id, "userId": userId})
