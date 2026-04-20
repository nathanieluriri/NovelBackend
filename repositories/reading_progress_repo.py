import asyncio
from datetime import datetime, timezone

from core.database import ASC, client
from schemas.reading_progress_schema import ReadingProgressRecord


READING_PROGRESS = "reading_progress"


_indexes_ready = False
_indexes_lock = asyncio.Lock()


async def ensure_reading_progress_indexes() -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    async with _indexes_lock:
        if _indexes_ready:
            return
        await client.ensure_index(
            READING_PROGRESS, [("userId", ASC)], unique=True, background=True
        )
        _indexes_ready = True


async def upsert_reading_progress(record: ReadingProgressRecord):
    await ensure_reading_progress_indexes()
    now = datetime.now(timezone.utc).isoformat()
    payload = record.model_dump(exclude_none=True)
    await client.update_one(
        READING_PROGRESS,
        {"userId": record.userId},
        {
            "set": {**payload, "dateUpdated": now},
            "set_on_insert": {"dateCreated": now},
        },
        upsert=True,
    )


async def get_reading_progress(user_id: str):
    await ensure_reading_progress_indexes()
    return await client.find_one(READING_PROGRESS, {"userId": user_id})
