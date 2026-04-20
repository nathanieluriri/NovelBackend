"""Database client abstraction.

Repositories should talk to `client` (a `DatabaseClient`) using the neutral
CRUD / update vocabulary defined below. The underlying driver (currently
Motor/MongoDB) is an implementation detail of this module: swapping in a
Postgres-backed driver means rewriting this file, not every repository.

Neutral update spec format (alternative to raw Mongo `$set`/`$inc`/... dicts):

    await client.update_one("users", by_id(uid), {"set": {"name": "A"}})
    await client.update_one("users", by_id(uid), {"inc": {"balance": -5}})
    await client.update_one(
        "users", by_id(uid), {"add_to_set": {"unlockedChapters": chapterId}}
    )
    await client.update_one(
        "users", {"userId": uid},
        {"set": {"x": 1}, "inc": {"count": 1}},
    )

Raw Mongo-style update docs (`{"$set": {...}}`) are still accepted for
backward compatibility, but new code should use the neutral form.
"""

import os
from typing import Any, Mapping

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, ReturnDocument

load_dotenv()

DB = os.getenv("DB_NAME")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

ASC = ASCENDING
DESC = DESCENDING

# Neutral update op -> Mongo operator. Centralised so a future SQL driver can
# translate the same neutral vocabulary into `UPDATE ... SET` expressions.
_UPDATE_OP_MAP = {
    "set": "$set",
    "unset": "$unset",
    "inc": "$inc",
    "push": "$push",
    "pull": "$pull",
    "add_to_set": "$addToSet",
    "set_on_insert": "$setOnInsert",
    "current_date": "$currentDate",
}


def _translate_update(update: Mapping[str, Any]) -> dict:
    if not update:
        return {}
    # Passthrough if the caller already used Mongo operators.
    if any(k.startswith("$") for k in update):
        return dict(update)
    translated: dict = {}
    for key, value in update.items():
        op = _UPDATE_OP_MAP.get(key)
        if op is None:
            raise ValueError(f"Unknown update op: {key!r}")
        translated[op] = value
    return translated


def to_id(value: Any) -> ObjectId:
    """Coerce an external id (string/ObjectId) to the driver's primary key type.

    Raises `InvalidId` for malformed input; callers that want silent handling
    should use `maybe_id`.
    """
    if isinstance(value, ObjectId):
        return value
    return ObjectId(value)


def maybe_id(value: Any) -> ObjectId | None:
    try:
        return to_id(value)
    except (InvalidId, TypeError):
        return None


def is_valid_id(value: Any) -> bool:
    return isinstance(value, ObjectId) or (
        isinstance(value, str) and ObjectId.is_valid(value)
    )


def by_id(value: Any) -> dict:
    """Build a primary-key filter. Routes through the driver's id type so that
    repositories don't need to know whether ids are ObjectIds or strings."""
    return {"_id": to_id(value)}


class DatabaseClient:
    """Thin driver-neutral wrapper over a Motor database.

    Only the methods on this class should appear in repository code. Anything
    that isn't expressible here (e.g. Mongo aggregation pipelines) goes
    through `aggregate` explicitly, which makes the non-portable surface easy
    to find when a SQL migration comes.
    """

    def __init__(self, motor_db):
        self._db = motor_db

    @property
    def raw(self):
        """Escape hatch for code that still needs direct Motor access."""
        return self._db

    async def find_one(
        self,
        collection: str,
        filter: Mapping[str, Any],
        *,
        projection: Mapping[str, Any] | None = None,
    ):
        return await self._db[collection].find_one(filter, projection)

    async def find_many(
        self,
        collection: str,
        filter: Mapping[str, Any] | None = None,
        *,
        projection: Mapping[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[dict]:
        cursor = self._db[collection].find(filter or {}, projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)
        return [doc async for doc in cursor]

    async def insert_one(self, collection: str, document: Mapping[str, Any]) -> Any:
        result = await self._db[collection].insert_one(dict(document))
        return result.inserted_id

    async def insert_and_fetch(
        self, collection: str, document: Mapping[str, Any]
    ) -> dict | None:
        inserted_id = await self.insert_one(collection, document)
        return await self._db[collection].find_one({"_id": inserted_id})

    async def update_one(
        self,
        collection: str,
        filter: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> int:
        result = await self._db[collection].update_one(
            filter, _translate_update(update), upsert=upsert
        )
        return result.modified_count

    async def update_many(
        self,
        collection: str,
        filter: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> int:
        result = await self._db[collection].update_many(
            filter, _translate_update(update)
        )
        return result.modified_count

    async def delete_one(self, collection: str, filter: Mapping[str, Any]) -> int:
        result = await self._db[collection].delete_one(filter)
        return result.deleted_count

    async def delete_many(self, collection: str, filter: Mapping[str, Any]) -> int:
        result = await self._db[collection].delete_many(filter)
        return result.deleted_count

    async def count(
        self, collection: str, filter: Mapping[str, Any] | None = None
    ) -> int:
        return await self._db[collection].count_documents(filter or {})

    async def find_one_and_update(
        self,
        collection: str,
        filter: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        return_after: bool = True,
        upsert: bool = False,
        projection: Mapping[str, Any] | None = None,
    ):
        return await self._db[collection].find_one_and_update(
            filter,
            _translate_update(update),
            return_document=(
                ReturnDocument.AFTER if return_after else ReturnDocument.BEFORE
            ),
            upsert=upsert,
            projection=projection,
        )

    async def find_one_and_delete(
        self, collection: str, filter: Mapping[str, Any]
    ):
        return await self._db[collection].find_one_and_delete(filter)

    async def aggregate(
        self,
        collection: str,
        pipeline: list[Mapping[str, Any]],
        *,
        length: int | None = None,
    ) -> list[dict]:
        """Non-portable: pipelines will need rewriting for a SQL backend."""
        return await self._db[collection].aggregate(pipeline).to_list(length=length)

    async def ensure_index(
        self, collection: str, keys: list[tuple[str, int]], **options
    ):
        return await self._db[collection].create_index(keys, **options)


_motor_client = AsyncIOMotorClient(MONGO_URL)
_motor_db = _motor_client[DB]

# Raw Motor database kept for backward compatibility and aggregation edge
# cases. New repository code should prefer `client`.
db = _motor_db
client = DatabaseClient(_motor_db)
