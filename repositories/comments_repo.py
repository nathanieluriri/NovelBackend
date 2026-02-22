from bson import ObjectId, errors
from pymongo import ASCENDING, DESCENDING

from core.database import db
from schemas.comments_schema import CommentCreate, InteractionTargetType


async def ensure_comment_indexes():
    await db.comments.create_index(
        [("targetType", ASCENDING), ("targetId", ASCENDING), ("dateCreated", DESCENDING)],
        background=True,
    )
    await db.comments.create_index(
        [("userId", ASCENDING), ("dateCreated", DESCENDING)],
        background=True,
    )


async def get_all_user_comments(userId: str, skip: int = 0, limit: int = 20):
    await ensure_comment_indexes()
    cursor = db.comments.find({"userId": userId}).skip(skip).limit(limit)
    return [comment async for comment in cursor]


async def count_all_user_comments(userId: str) -> int:
    await ensure_comment_indexes()
    return await db.comments.count_documents({"userId": userId})


async def get_comments_by_target(
    targetType: InteractionTargetType,
    targetId: str,
    skip: int = 0,
    limit: int = 20,
):
    await ensure_comment_indexes()
    query = {"targetType": targetType.value, "targetId": targetId}
    # Compatibility with legacy chapter-only comments.
    if targetType == InteractionTargetType.chapter:
        query = {
            "$or": [
                {"targetType": targetType.value, "targetId": targetId},
                {"chapterId": targetId},
            ]
        }
    cursor = db.comments.find(query).skip(skip).limit(limit)
    return [comment async for comment in cursor]


async def count_comments_by_target(
    targetType: InteractionTargetType,
    targetId: str,
) -> int:
    await ensure_comment_indexes()
    query = {"targetType": targetType.value, "targetId": targetId}
    if targetType == InteractionTargetType.chapter:
        query = {
            "$or": [
                {"targetType": targetType.value, "targetId": targetId},
                {"chapterId": targetId},
            ]
        }
    return await db.comments.count_documents(query)


async def get_all_chapter_comments(chapterId: str, skip: int = 0, limit: int = 20):
    # Compatibility wrapper.
    return await get_comments_by_target(
        targetType=InteractionTargetType.chapter,
        targetId=chapterId,
        skip=skip,
        limit=limit,
    )


async def delete_comments_with_chapter_id(chapterIds: list):
    return await db.comments.delete_many(
        {
            "$or": [
                {"chapterId": {"$in": chapterIds}},
                {"targetType": InteractionTargetType.chapter.value, "targetId": {"$in": chapterIds}},
            ]
        }
    )


async def delete_comments_with_user_id(userIds: list):
    return await db.comments.delete_many({"userId": {"$in": userIds}})


async def create_comment(comment_data: CommentCreate):
    await ensure_comment_indexes()
    comment = comment_data.model_dump()
    result = await db.comments.insert_one(comment)
    return await db.comments.find_one({"_id": result.inserted_id})


async def delete_comment_with_comment_id(commentId: str):
    try:
        obj_id = ObjectId(commentId)
    except errors.InvalidId:
        return None
    return await db.comments.find_one_and_delete({"_id": obj_id})


async def update_comment_with_comment_id(commentId: str, userId: str, text: str):
    try:
        obj_id = ObjectId(commentId)
    except errors.InvalidId:
        return None

    await db.comments.update_one(
        {"_id": obj_id, "userId": userId},
        {"$set": {"text": text}},
    )
    return await db.comments.find_one({"_id": obj_id, "userId": userId})


async def delete_comment_with_comment_id_userId(userId: str, commentId: str):
    try:
        obj_id = ObjectId(commentId)
    except errors.InvalidId:
        return None
    return await db.comments.find_one_and_delete({"_id": obj_id, "userId": userId})
