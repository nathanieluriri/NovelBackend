import asyncio
from datetime import datetime, timezone

from core.database import ASC, client
from schemas.google_oauth_schema import (
    GoogleOAuthExchangeRecord,
    GoogleOAuthExchangeRecordCreate,
)


GOOGLE_OAUTH_EXCHANGES = "google_oauth_exchanges"


_indexes_ready = False
_indexes_lock = asyncio.Lock()


async def ensure_google_oauth_exchange_indexes() -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    async with _indexes_lock:
        if _indexes_ready:
            return

        await client.ensure_index(
            GOOGLE_OAUTH_EXCHANGES,
            [("codeHash", ASC)],
            unique=True,
            background=True,
        )
        # TTL: expired exchanges get deleted automatically.
        await client.ensure_index(
            GOOGLE_OAUTH_EXCHANGES,
            [("expiresAt", ASC)],
            expireAfterSeconds=0,
            background=True,
        )
        _indexes_ready = True


async def create_google_oauth_exchange(
    exchange_record: GoogleOAuthExchangeRecordCreate,
) -> GoogleOAuthExchangeRecord:
    await ensure_google_oauth_exchange_indexes()
    created = await client.insert_and_fetch(
        GOOGLE_OAUTH_EXCHANGES, exchange_record.model_dump()
    )
    assert created is not None
    return GoogleOAuthExchangeRecord(**created)


async def consume_google_oauth_exchange(
    code_hash: str,
) -> GoogleOAuthExchangeRecord | None:
    await ensure_google_oauth_exchange_indexes()
    now = datetime.now(timezone.utc)
    # Atomic: only consume rows that are still unconsumed and unexpired.
    result = await client.find_one_and_update(
        GOOGLE_OAUTH_EXCHANGES,
        {
            "codeHash": code_hash,
            "consumedAt": None,
            "expiresAt": {"$gt": now},
        },
        {"set": {"consumedAt": now}},
        return_after=False,
    )
    if result is None:
        return None
    return GoogleOAuthExchangeRecord(**result)
