import asyncio

from core.database import ASC, DESC, client, maybe_id
from schemas.bookmark_schema import BookMarkCreate, InteractionTargetType


BOOKMARKS = "bookmarks"


_bookmark_indexes_ready = False
_bookmark_indexes_lock = asyncio.Lock()


async def ensure_bookmark_indexes() -> None:
    global _bookmark_indexes_ready
    if _bookmark_indexes_ready:
        return
    async with _bookmark_indexes_lock:
        if _bookmark_indexes_ready:
            return
        await client.ensure_index(
            BOOKMARKS,
            [("userId", ASC), ("targetType", ASC), ("targetId", ASC)],
            unique=True,
            partialFilterExpression={
                "targetType": {"$exists": True},
                "targetId": {"$exists": True},
            },
            background=True,
        )
        await client.ensure_index(
            BOOKMARKS,
            [("userId", ASC), ("dateCreated", DESC)],
            background=True,
        )
        _bookmark_indexes_ready = True


async def get_all_user_bookmarks(
    userId: str,
    targetType: InteractionTargetType | None = None,
    skip: int = 0,
    limit: int = 20,
):
    await ensure_bookmark_indexes()
    query: dict = {"userId": userId}
    if targetType is not None:
        query["targetType"] = targetType.value
    return await client.find_many(BOOKMARKS, query, skip=skip, limit=limit)


async def count_user_bookmarks(
    userId: str,
    targetType: InteractionTargetType | None = None,
) -> int:
    query: dict = {"userId": userId}
    if targetType is not None:
        query["targetType"] = targetType.value
    return await client.count(BOOKMARKS, query)


async def get_bookmark_by_user_target(
    userId: str, targetType: InteractionTargetType, targetId: str
):
    await ensure_bookmark_indexes()
    return await client.find_one(
        BOOKMARKS,
        {"userId": userId, "targetType": targetType.value, "targetId": targetId},
    )


async def delete_bookmarks_with_page_id(pageIds: list):
    if not pageIds:
        return None
    return await client.delete_many(
        BOOKMARKS,
        {
            "$or": [
                {"pageId": {"$in": pageIds}},
                {
                    "targetType": InteractionTargetType.page.value,
                    "targetId": {"$in": pageIds},
                },
            ]
        },
    )


async def delete_bookmarks_with_user_id(userIds: list):
    if not userIds:
        return None
    return await client.delete_many(BOOKMARKS, {"userId": {"$in": userIds}})


async def create_bookmark(bookmark_data: BookMarkCreate):
    await ensure_bookmark_indexes()
    return await client.insert_and_fetch(BOOKMARKS, bookmark_data.model_dump())


async def delete_bookmarks_with_bookmark_id(bookmarkId: str):
    oid = maybe_id(bookmarkId)
    if oid is None:
        return None
    return await client.find_one_and_delete(BOOKMARKS, {"_id": oid})


async def delete_bookmark_by_id_userId(bookmarkId: str, userId: str):
    oid = maybe_id(bookmarkId)
    if oid is None:
        return None
    return await client.find_one_and_delete(
        BOOKMARKS, {"_id": oid, "userId": userId}
    )
