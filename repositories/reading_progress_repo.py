from datetime import datetime, timezone

from pymongo import ASCENDING

from core.database import db
from schemas.reading_progress_schema import ReadingProgressRecord


async def ensure_reading_progress_indexes():
    await db.reading_progress.create_index([("userId", ASCENDING)], unique=True, background=True)


async def upsert_reading_progress(record: ReadingProgressRecord):
    await ensure_reading_progress_indexes()
    now = datetime.now(timezone.utc).isoformat()
    payload = record.model_dump(exclude_none=True)
    await db.reading_progress.update_one(
        {"userId": record.userId},
        {
            "$set": {
                **payload,
                "dateUpdated": now,
            },
            "$setOnInsert": {"dateCreated": now},
        },
        upsert=True,
    )


async def get_reading_progress(user_id: str):
    await ensure_reading_progress_indexes()
    return await db.reading_progress.find_one({"userId": user_id})
