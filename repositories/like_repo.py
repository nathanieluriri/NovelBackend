import asyncio

from pymongo.errors import DuplicateKeyError

from core.database import ASC, client, maybe_id
from schemas.likes_schema import LikeCreate


LIKES = "likes"


_like_indexes_ready = False
_like_indexes_lock = asyncio.Lock()


async def ensure_like_indexes() -> None:
    global _like_indexes_ready
    if _like_indexes_ready:
        return
    async with _like_indexes_lock:
        if _like_indexes_ready:
            return
        # Prevents duplicate (userId, chapterId) likes at the DB layer instead
        # of the check-then-insert race that used to live in `create_like`.
        await client.ensure_index(
            LIKES,
            [("userId", ASC), ("chapterId", ASC)],
            unique=True,
            background=True,
        )
        await client.ensure_index(LIKES, [("chapterId", ASC)], background=True)
        _like_indexes_ready = True


async def get_all_user_likes(userId, skip: int = 0, limit: int | None = None):
    return await client.find_many(
        LIKES, {"userId": userId}, skip=skip, limit=limit
    )


async def count_user_likes(userId: str) -> int:
    return await client.count(LIKES, {"userId": userId})


async def get_all_chapter_likes(
    chapterId, skip: int = 0, limit: int | None = None
):
    return await client.find_many(
        LIKES, {"chapterId": chapterId}, skip=skip, limit=limit
    )


async def count_likes_by_chapter(chapterId: str) -> int:
    return await client.count(LIKES, {"chapterId": chapterId})


async def get_chapter_like_user_stats(
    chapterId: str, skip: int = 0, limit: int = 20
):
    pipeline = [
        {"$match": {"chapterId": chapterId}},
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
    return await client.aggregate(LIKES, pipeline, length=limit)


async def count_chapter_like_users(chapterId: str) -> int:
    pipeline = [
        {"$match": {"chapterId": chapterId}},
        {"$group": {"_id": "$userId"}},
        {"$count": "total"},
    ]
    result = await client.aggregate(LIKES, pipeline, length=1)
    if not result:
        return 0
    return int(result[0].get("total", 0))


async def delete_likes_with_page_id(chapterId: list):
    """Delete all likes for the given chapter ids."""
    if not chapterId:
        return None
    return await client.delete_many(LIKES, {"chapterId": {"$in": chapterId}})


async def delete_likes_with_user_id(userId: list):
    """Delete all likes for the given user ids."""
    if not userId:
        return None
    return await client.delete_many(LIKES, {"userId": {"$in": userId}})


async def create_like(like_data: LikeCreate):
    await ensure_like_indexes()
    like = like_data.model_dump()
    try:
        inserted_id = await client.insert_one(LIKES, like)
    except DuplicateKeyError:
        # Idempotent: if the like already exists, return it rather than
        # raising — matches the previous behaviour of the check-then-insert.
        return await client.find_one(
            LIKES,
            {"userId": like_data.userId, "chapterId": like_data.chapterId},
        )
    return await client.find_one(LIKES, {"_id": inserted_id})


async def delete_like_with_like_id(likeId: str):
    oid = maybe_id(likeId)
    if oid is None:
        return None
    return await client.find_one_and_delete(LIKES, {"_id": oid})
