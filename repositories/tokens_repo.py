import asyncio
from datetime import datetime, timedelta

from dateutil import parser
from fastapi import HTTPException

from core.database import ASC, client, maybe_id
from schemas.tokens_schema import (
    accessTokenCreate,
    accessTokenOut,
    refreshTokenCreate,
    refreshTokenOut,
)


ACCESS_TOKENS = "accessToken"
REFRESH_TOKENS = "refreshToken"


_token_indexes_ready = False
_token_indexes_lock = asyncio.Lock()


async def ensure_token_indexes() -> None:
    global _token_indexes_ready
    if _token_indexes_ready:
        return
    async with _token_indexes_lock:
        if _token_indexes_ready:
            return
        await client.ensure_index(
            ACCESS_TOKENS, [("userId", ASC)], background=True
        )
        await client.ensure_index(
            REFRESH_TOKENS, [("userId", ASC)], background=True
        )
        _token_indexes_ready = True


async def add_access_tokens(
    token_data: accessTokenCreate,
) -> accessTokenOut:
    await ensure_token_indexes()
    token = token_data.model_dump()
    token["role"] = "member"
    created = await client.insert_and_fetch(ACCESS_TOKENS, token)
    assert created is not None
    return accessTokenOut(**created)


async def add_admin_access_tokens(
    token_data: accessTokenCreate,
) -> accessTokenOut:
    await ensure_token_indexes()
    token = token_data.model_dump()
    token["role"] = "admin"
    token["status"] = "inactive"
    created = await client.insert_and_fetch(ACCESS_TOKENS, token)
    assert created is not None
    return accessTokenOut(**created)


async def update_admin_access_tokens(token: str) -> accessTokenOut:
    oid = maybe_id(token)
    if oid is None:
        raise HTTPException(status_code=401, detail="Invalid Access Id")
    updated = await client.find_one_and_update(
        ACCESS_TOKENS,
        {"_id": oid},
        {"set": {"status": "active"}},
    )
    assert updated is not None
    return accessTokenOut(**updated)


async def add_refresh_tokens(
    token_data: refreshTokenCreate,
) -> refreshTokenOut:
    await ensure_token_indexes()
    created = await client.insert_and_fetch(
        REFRESH_TOKENS, token_data.model_dump()
    )
    assert created is not None
    return refreshTokenOut(**created)


async def delete_access_token(accessToken):
    oid = maybe_id(accessToken)
    if oid is None:
        return
    await client.find_one_and_delete(ACCESS_TOKENS, {"_id": oid})


async def delete_refresh_token(refreshToken: str):
    oid = maybe_id(refreshToken)
    if oid is None:
        raise HTTPException(status_code=401, detail="Invalid Refresh Id")
    result = await client.find_one_and_delete(REFRESH_TOKENS, {"_id": oid})
    if result:
        return True


def is_older_than_days(date_string, days=10):
    created_date = parser.isoparse(date_string)
    now = datetime.utcnow().replace(tzinfo=created_date.tzinfo)
    return (now - created_date) > timedelta(days=days)


async def get_access_tokens(accessToken: str):
    oid = maybe_id(accessToken)
    if oid is None:
        return None
    token = await client.find_one(ACCESS_TOKENS, {"_id": oid})
    if not token:
        print("No token found")
        return None
    if is_older_than_days(date_string=token["dateCreated"]):
        await delete_access_token(accessToken=str(token["_id"]))
        return None

    role = token.get("role")
    if role == "member":
        return accessTokenOut(**token)
    if role == "admin":
        if token.get("status") == "active":
            return accessTokenOut(**token)
        return "inactive"
    return None


async def get_refresh_tokens(refreshToken: str):
    oid = maybe_id(refreshToken)
    if oid is None:
        return None
    token = await client.find_one(REFRESH_TOKENS, {"_id": oid})
    if token:
        return refreshTokenOut(**token)
    return None


async def delete_all_tokens_with_user_id(userId: str):
    await ensure_token_indexes()
    await client.delete_many(REFRESH_TOKENS, {"userId": userId})
    await client.delete_many(ACCESS_TOKENS, {"userId": userId})
