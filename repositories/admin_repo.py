from typing import List

from core.database import by_id, client, maybe_id
from schemas.admin_schema import (
    AllowedAdminCreate,
    DefaultAllowedAdminCreate,
    NewAdminCreate,
    NewAdminOut,
)
from schemas.email_schema import ClientData


ADMINS = "admins"
ALLOWED_ADMINS = "AllowedAdmins"
ACCESS_TOKENS = "accessToken"
LOGIN_ATTEMPTS = "LoginAttempts"


async def get_admin_by_email(email: str) -> NewAdminOut | None:
    admin = await client.find_one(ADMINS, {"email": email})
    if not admin:
        return None
    try:
        return NewAdminOut(**admin)
    except TypeError:
        print("no admin user for the email")
        return None


async def get_all_admins() -> List[NewAdminOut] | None:
    admins = await client.find_many(ADMINS)
    try:
        return [NewAdminOut(**admin) for admin in admins]
    except TypeError:
        print("no admin user for the email")
        return None


async def get_all_users() -> List[NewAdminOut] | None:
    # Preserves the legacy (mis-named) behaviour of reading from `admins`.
    return await get_all_admins()


async def get_admin_by_email_return_dict(email: str) -> dict | None:
    return await client.find_one(ADMINS, {"email": email})


async def create_admin(user_data: NewAdminCreate):
    return await client.insert_and_fetch(ADMINS, user_data.model_dump())


async def create_allowed_admin(user_data: AllowedAdminCreate):
    return await client.insert_and_fetch(
        ALLOWED_ADMINS, user_data.model_dump()
    )


async def delete_admin_by_email_and_provider(email: str, provider: str):
    # The previous implementation silently ignored `provider`. We now honour
    # it so that multi-provider admins only lose the intended record.
    return await client.delete_one(
        ADMINS,
        {
            "email": email,
            "$or": [{"provider": provider}, {"authProviders": provider}],
        },
    )


async def get_allowd_admin_emails(email: str):
    admin = await client.find_one(ALLOWED_ADMINS, {"email": email})
    if not admin:
        print("this email isn't allowed to register as an admin")
        return False
    try:
        NewAdminOut(**admin)
        return True
    except TypeError as e:
        print("TypeError while parsing admin data:", e)
        return False


async def create_email_list_for_admins(email: str):
    return await client.insert_and_fetch(ALLOWED_ADMINS, {"email": email})


async def get_admin_details_with_accessToken(accessToken: str):
    token_oid = maybe_id(accessToken)
    if token_oid is None:
        return None
    token_doc = await client.find_one(ACCESS_TOKENS, {"_id": token_oid})
    if not token_doc:
        return None
    admin_oid = maybe_id(token_doc.get("userId"))
    if admin_oid is None:
        return None
    return await client.find_one(ADMINS, {"_id": admin_oid})


async def get_location_details_for_admin(user_id: str) -> ClientData | None:
    try:
        location_doc = await client.find_one_and_delete(
            LOGIN_ATTEMPTS, {"userId": user_id}
        )
        if location_doc:
            return ClientData(**location_doc)
        return None
    except Exception as e:
        print(e)
        raise


async def replace_password_admin(userId: str, hashedPassword: str):
    await client.find_one_and_update(
        ADMINS,
        by_id(userId),
        {"set": {"password": hashedPassword}},
    )


async def create_default_admin(user_data: DefaultAllowedAdminCreate):
    user = user_data.model_dump()
    existing = await client.find_one(ALLOWED_ADMINS, {"email": user["email"]})
    if existing:
        return 0
    return await client.insert_and_fetch(ALLOWED_ADMINS, user)


async def update_admin_profile(userId: str, update: dict):
    await client.find_one_and_update(
        ADMINS,
        by_id(userId),
        {"set": update},
    )
