from core.database import db
from schemas.entitlement_schema import EntitlementCreate, EntitlementOut
from pymongo import ASCENDING


entitlement_collection = db.entitlements


async def ensure_entitlement_indexes():
    await entitlement_collection.create_index(
        [("userId", ASCENDING), ("chapterId", ASCENDING)],
        unique=True,
        background=True,
    )


async def has_chapter_entitlement(userId: str, chapterId: str) -> bool:
    await ensure_entitlement_indexes()
    found = await entitlement_collection.find_one({"userId": userId, "chapterId": chapterId})
    return found is not None


async def create_chapter_entitlement_if_absent(
    userId: str,
    chapterId: str,
    source: str = "stars_wallet",
    tx_ref: str | None = None,
):
    await ensure_entitlement_indexes()
    existing = await entitlement_collection.find_one({"userId": userId, "chapterId": chapterId})
    if existing:
        return EntitlementOut(**existing), False

    created = EntitlementCreate(
        userId=userId,
        chapterId=chapterId,
        source=source,
        txRef=tx_ref,
    )
    result = await entitlement_collection.insert_one(created.model_dump())
    new_doc = await entitlement_collection.find_one({"_id": result.inserted_id})
    return EntitlementOut(**new_doc), True # type: ignore
