import asyncio

from core.database import ASC, client
from schemas.entitlement_schema import EntitlementCreate, EntitlementOut


ENTITLEMENTS = "entitlements"


_entitlement_indexes_ready = False
_entitlement_indexes_lock = asyncio.Lock()


async def ensure_entitlement_indexes() -> None:
    global _entitlement_indexes_ready
    if _entitlement_indexes_ready:
        return
    async with _entitlement_indexes_lock:
        if _entitlement_indexes_ready:
            return
        await client.ensure_index(
            ENTITLEMENTS,
            [("userId", ASC), ("chapterId", ASC)],
            unique=True,
            background=True,
        )
        _entitlement_indexes_ready = True


async def has_chapter_entitlement(userId: str, chapterId: str) -> bool:
    await ensure_entitlement_indexes()
    found = await client.find_one(
        ENTITLEMENTS,
        {"userId": userId, "chapterId": chapterId},
        projection={"_id": 1},
    )
    return found is not None


async def create_chapter_entitlement_if_absent(
    userId: str,
    chapterId: str,
    source: str = "stars_wallet",
    tx_ref: str | None = None,
):
    await ensure_entitlement_indexes()
    existing = await client.find_one(
        ENTITLEMENTS, {"userId": userId, "chapterId": chapterId}
    )
    if existing:
        return EntitlementOut(**existing), False

    created = EntitlementCreate(
        userId=userId,
        chapterId=chapterId,
        source=source,
        txRef=tx_ref,
    )
    new_doc = await client.insert_and_fetch(ENTITLEMENTS, created.model_dump())
    assert new_doc is not None
    return EntitlementOut(**new_doc), True
