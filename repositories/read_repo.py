import asyncio
from datetime import datetime, timezone

from core.database import ASC, client
from schemas.read_schema import MarkAsRead


READ = "read"


_read_indexes_ready = False
_read_indexes_lock = asyncio.Lock()


async def ensure_read_indexes() -> None:
    global _read_indexes_ready
    if _read_indexes_ready:
        return
    async with _read_indexes_lock:
        if _read_indexes_ready:
            return
        try:
            await client.ensure_index(
                READ,
                [("userId", ASC), ("chapterId", ASC)],
                unique=True,
                background=True,
            )
        except Exception as e:
            # Don't fail startup if an index rebuild conflicts; log and move
            # on so reads still work.
            print(f"Error ensuring read index: {e}")
        _read_indexes_ready = True


async def get_all_chapters_user_has_read(userId):
    await ensure_read_indexes()
    return await client.find_many(READ, {"userId": userId})


async def get_particular_chapter_user_has_read(
    userId: str, chapterId: str
) -> MarkAsRead:
    await ensure_read_indexes()
    result = await client.find_one(
        READ, {"userId": userId, "chapterId": chapterId}
    )
    if result:
        return MarkAsRead(**result)
    return MarkAsRead(userId=userId, chapterId=chapterId, hasRead=False)


async def upsert_read_record(data: MarkAsRead):
    await ensure_read_indexes()
    try:
        await client.update_one(
            READ,
            {"userId": data.userId, "chapterId": data.chapterId},
            {
                "set": data.model_dump(),
                "current_date": {"lastUpdated": True},
                "set_on_insert": {
                    "dateCreated": datetime.now(timezone.utc).isoformat()
                },
            },
            upsert=True,
        )
    except Exception as e:
        print(
            f"Error during upsert for userId: {data.userId}, "
            f"chapterId: {data.chapterId}: {e}"
        )
        raise
