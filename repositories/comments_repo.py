import asyncio

from core.database import ASC, DESC, client, maybe_id
from schemas.comments_schema import CommentCreate, InteractionTargetType


COMMENTS = "comments"


_comment_indexes_ready = False
_comment_indexes_lock = asyncio.Lock()


async def ensure_comment_indexes() -> None:
    global _comment_indexes_ready
    if _comment_indexes_ready:
        return
    async with _comment_indexes_lock:
        if _comment_indexes_ready:
            return
        await client.ensure_index(
            COMMENTS,
            [("targetType", ASC), ("targetId", ASC), ("dateCreated", DESC)],
            background=True,
        )
        await client.ensure_index(
            COMMENTS,
            [("userId", ASC), ("dateCreated", DESC)],
            background=True,
        )
        _comment_indexes_ready = True


async def get_all_user_comments(userId: str, skip: int = 0, limit: int = 20):
    await ensure_comment_indexes()
    return await client.find_many(
        COMMENTS, {"userId": userId}, skip=skip, limit=limit
    )


async def count_all_user_comments(userId: str) -> int:
    return await client.count(COMMENTS, {"userId": userId})


def _target_query(targetType: InteractionTargetType, targetId: str) -> dict:
    # Chapter comments predate the generic target model; the `$or` fallback
    # keeps legacy rows (`chapterId`) readable alongside the new shape.
    if targetType == InteractionTargetType.chapter:
        return {
            "$or": [
                {"targetType": targetType.value, "targetId": targetId},
                {"chapterId": targetId},
            ]
        }
    return {"targetType": targetType.value, "targetId": targetId}


async def get_comments_by_target(
    targetType: InteractionTargetType,
    targetId: str,
    skip: int = 0,
    limit: int = 20,
):
    await ensure_comment_indexes()
    return await client.find_many(
        COMMENTS, _target_query(targetType, targetId), skip=skip, limit=limit
    )


async def count_comments_by_target(
    targetType: InteractionTargetType,
    targetId: str,
) -> int:
    await ensure_comment_indexes()
    return await client.count(COMMENTS, _target_query(targetType, targetId))


def _chapter_comment_query(chapterId: str) -> dict:
    return _target_query(InteractionTargetType.chapter, chapterId)


async def get_chapter_comment_user_stats(
    chapterId: str, skip: int = 0, limit: int = 20
):
    await ensure_comment_indexes()
    pipeline = [
        {"$match": _chapter_comment_query(chapterId)},
        {
            "$group": {
                "_id": "$userId",
                "interactionCount": {"$sum": 1},
                "lastInteractionAt": {"$max": "$dateCreated"},
            }
        },
        {"$sort": {"lastInteractionAt": -1, "_id": 1}},
        {"$skip": skip},
        {"$limit": limit},
    ]
    return await client.aggregate(COMMENTS, pipeline, length=limit)


async def count_chapter_comment_users(chapterId: str) -> int:
    await ensure_comment_indexes()
    pipeline = [
        {"$match": _chapter_comment_query(chapterId)},
        {"$group": {"_id": "$userId"}},
        {"$count": "total"},
    ]
    result = await client.aggregate(COMMENTS, pipeline, length=1)
    if not result:
        return 0
    return int(result[0].get("total", 0))


async def get_all_chapter_comments(chapterId: str, skip: int = 0, limit: int = 20):
    return await get_comments_by_target(
        targetType=InteractionTargetType.chapter,
        targetId=chapterId,
        skip=skip,
        limit=limit,
    )


async def delete_comments_with_chapter_id(chapterIds: list):
    if not chapterIds:
        return None
    return await client.delete_many(
        COMMENTS,
        {
            "$or": [
                {"chapterId": {"$in": chapterIds}},
                {
                    "targetType": InteractionTargetType.chapter.value,
                    "targetId": {"$in": chapterIds},
                },
            ]
        },
    )


async def delete_comments_with_user_id(userIds: list):
    if not userIds:
        return None
    return await client.delete_many(COMMENTS, {"userId": {"$in": userIds}})


async def create_comment(comment_data: CommentCreate):
    await ensure_comment_indexes()
    return await client.insert_and_fetch(COMMENTS, comment_data.model_dump())


async def delete_comment_with_comment_id(commentId: str):
    oid = maybe_id(commentId)
    if oid is None:
        return None
    return await client.find_one_and_delete(COMMENTS, {"_id": oid})


async def update_comment_with_comment_id(commentId: str, userId: str, text: str):
    oid = maybe_id(commentId)
    if oid is None:
        return None
    await client.update_one(
        COMMENTS,
        {"_id": oid, "userId": userId},
        {"set": {"text": text}},
    )
    return await client.find_one(COMMENTS, {"_id": oid, "userId": userId})


async def delete_comment_with_comment_id_userId(userId: str, commentId: str):
    oid = maybe_id(commentId)
    if oid is None:
        return None
    return await client.find_one_and_delete(
        COMMENTS, {"_id": oid, "userId": userId}
    )
