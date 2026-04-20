from typing import List

from core.database import by_id, client, is_valid_id, maybe_id
from schemas.user_schema import NewUserCreate


async def get_user_by_email(email: str):
    return await client.find_one("users", {"email": email})


async def checks_user_balance(userId: str):
    oid = maybe_id(userId)
    if oid is None:
        return None
    user = await client.find_one(
        "users", {"_id": oid}, projection={"balance": 1}
    )
    if user is None:
        return None
    return user.get("balance")


async def subtract_from_user_balance(userId, number_of_stars):
    oid = maybe_id(userId)
    if oid is None:
        return None
    await client.update_one(
        "users",
        {"_id": oid},
        {"inc": {"balance": -number_of_stars}},
    )


async def add_to_user_balance(userId, number_of_stars):
    oid = maybe_id(userId)
    if oid is None:
        return None
    await client.update_one(
        "users",
        {"_id": oid},
        {"inc": {"balance": number_of_stars}},
    )


async def update_user_unlocked_chapters(userId, chapterId):
    oid = maybe_id(userId)
    if oid is None:
        return None
    updated = await client.find_one_and_update(
        "users",
        {"_id": oid},
        {"add_to_set": {"unlockedChapters": chapterId}},
    )
    if updated is None:
        return None
    return True


async def update_user_subscription(userId: str, subscription: dict):
    oid = maybe_id(userId)
    if oid is None:
        return None
    await client.update_one(
        "users",
        {"_id": oid},
        {"set": {"subscription": subscription}},
    )
    return True


async def get_all_users(skip: int = 0, limit: int | None = None):
    return await client.find_many("users", skip=skip, limit=limit)


async def create_user(user_data: NewUserCreate):
    return await client.insert_and_fetch("users", user_data.model_dump())


async def get_user_by_email_and_provider(email: str, provider: str):
    return await client.find_one(
        "users",
        {
            "email": email,
            "$or": [
                {"provider": provider},
                {"authProviders": provider},
            ],
        },
    )


async def get_user_by_userId(userId: str):
    oid = maybe_id(userId)
    if oid is None:
        return None
    return await client.find_one("users", {"_id": oid})


async def get_users_by_user_ids(userIds: List[str]):
    object_ids = [maybe_id(uid) for uid in userIds if is_valid_id(uid)]
    object_ids = [oid for oid in object_ids if oid is not None]
    if not object_ids:
        return []
    return await client.find_many("users", {"_id": {"$in": object_ids}})


async def replace_password(userId: str, hashedPassword: str):
    await client.find_one_and_update(
        "users",
        by_id(userId),
        {"set": {"password": hashedPassword}},
    )


async def update_user_profile(userId: str, update: dict):
    return await client.find_one_and_update(
        "users",
        by_id(userId),
        {"set": update},
    )


async def add_auth_provider_to_user(
    user_id: str,
    provider: str,
    profile_updates: dict | None = None,
):
    update_spec: dict = {"add_to_set": {"authProviders": provider}}
    if profile_updates:
        update_spec["set"] = profile_updates
    return await client.find_one_and_update(
        "users",
        by_id(user_id),
        update_spec,
    )
