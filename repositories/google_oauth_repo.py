import asyncio
from datetime import datetime, timezone

from pymongo import ASCENDING, ReturnDocument

from core.database import db
from schemas.google_oauth_schema import GoogleOAuthExchangeRecord, GoogleOAuthExchangeRecordCreate


_google_oauth_indexes_ready = False
_google_oauth_indexes_lock = asyncio.Lock()
_google_oauth_exchange_collection = db.google_oauth_exchanges


async def ensure_google_oauth_exchange_indexes() -> None:
    global _google_oauth_indexes_ready
    if _google_oauth_indexes_ready:
        return

    async with _google_oauth_indexes_lock:
        if _google_oauth_indexes_ready:
            return

        await _google_oauth_exchange_collection.create_index(
            [("codeHash", ASCENDING)],
            unique=True,
            background=True,
        )
        await _google_oauth_exchange_collection.create_index(
            [("expiresAt", ASCENDING)],
            expireAfterSeconds=0,
            background=True,
        )
        _google_oauth_indexes_ready = True


async def create_google_oauth_exchange(
    exchange_record: GoogleOAuthExchangeRecordCreate,
) -> GoogleOAuthExchangeRecord:
    await ensure_google_oauth_exchange_indexes()
    payload = exchange_record.model_dump()
    result = await _google_oauth_exchange_collection.insert_one(payload)
    created = await _google_oauth_exchange_collection.find_one({"_id": result.inserted_id})
    return GoogleOAuthExchangeRecord(**created)


async def consume_google_oauth_exchange(code_hash: str) -> GoogleOAuthExchangeRecord | None:
    await ensure_google_oauth_exchange_indexes()
    now = datetime.now(timezone.utc)
    result = await _google_oauth_exchange_collection.find_one_and_update(
        {
            "codeHash": code_hash,
            "consumedAt": None,
            "expiresAt": {"$gt": now},
        },
        {"$set": {"consumedAt": now}},
        return_document=ReturnDocument.BEFORE,
    )
    if result is None:
        return None
    return GoogleOAuthExchangeRecord(**result)
