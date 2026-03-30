import asyncio
from typing import Optional

from fastapi import HTTPException, status

from repositories.tokens_repo import delete_all_tokens_with_user_id, get_access_tokens
from repositories.user_repo import (
    create_user,
    get_user_by_email,
    get_user_by_email_and_provider,
    get_user_by_userId,
    replace_password,
    update_user_profile,
)
from schemas.tokens_schema import accessTokenOut
from schemas.user_schema import NewUserCreate, NewUserOut, OldUserBase, OldUserOut, UserOut, UserUpdate
from security.hash import check_password, hash_password
from security.tokens import generate_member_access_tokens, generate_refresh_tokens
from security.user_otp import generate_otp, send_otp_user, verify_otp
from services.bookmark_services import retrieve_user_bookmark
from services.like_services import retrieve_user_likes


async def _issue_member_tokens(user_id: str) -> tuple[str, str]:
    access_token = await generate_member_access_tokens(user_id)
    refresh_token = await generate_refresh_tokens(
        userId=user_id,
        accessToken=access_token.accesstoken,
    )
    return access_token.accesstoken, refresh_token.refreshtoken


async def _load_user_activity(user_id: str) -> tuple[list, list]:
    bookmarks, likes = await asyncio.gather(
        retrieve_user_bookmark(userId=user_id),
        retrieve_user_likes(userId=user_id),
    )
    return bookmarks, likes


async def build_authenticated_user_output(user_doc: dict) -> OldUserOut:
    user_id = str(user_doc["_id"])
    access_token, refresh_token = await _issue_member_tokens(user_id)
    bookmarks, likes = await _load_user_activity(user_id)
    return OldUserOut(
        **user_doc,
        accessToken=access_token,
        refreshToken=refresh_token,
        bookmarks=bookmarks,
        likes=likes,
    )


async def register_user(user_data: NewUserCreate) -> NewUserOut:
    existing = await get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    new_user = await create_user(user_data)
    user_out = UserOut(**new_user)
    access_token, refresh_token = await _issue_member_tokens(user_out.userId)
    user_out.accessToken = access_token
    user_out.refreshToken = refresh_token
    return NewUserOut(**user_out.model_dump())


async def login_credentials(user_data: OldUserBase) -> OldUserOut:
    existing = await get_user_by_email_and_provider(email=user_data.email, provider="credentials")
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User Not Found")

    hashed_password = existing.get("password")
    if hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password wasn't provided",
        )

    if not check_password(user_data.password, hashed=hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password Incorrect")

    return await build_authenticated_user_output(existing)


async def get_user_details_with_accessToken(token: str) -> Optional[UserOut]:
    token_out = await get_access_tokens(accessToken=token)
    if not isinstance(token_out, accessTokenOut):
        return None

    user_details = await get_user_by_userId(userId=token_out.userId)
    if user_details is None:
        return None

    bookmarks, likes = await _load_user_activity(token_out.userId)
    return UserOut(**user_details, bookmarks=bookmarks, likes=likes)


async def change_of_user_password_flow1(email):
    if await get_user_by_email(email=email):
        otp = generate_otp(email=email)
        await send_otp_user(otp=otp, user_email=email)
    else:
        raise HTTPException(status_code=404, detail="User Doesn't exist")


async def change_of_user_password_flow2(email, otp, password):
    is_valid = await verify_otp(email=email, otp=otp)
    if is_valid:
        hashed_password = hash_password(password=password)
        user = await get_user_by_email(email=email)
        await replace_password(userId=str(user["_id"]), hashedPassword=hashed_password)
        await delete_all_tokens_with_user_id(userId=str(user["_id"]))
        return True
    if is_valid is False:
        return False
    raise HTTPException(status_code=400, detail="Invalid password reset request")


async def update_user(token: str, update: UserUpdate):
    user = await get_user_details_with_accessToken(token=token)
    if user is None:
        raise HTTPException(status_code=404, detail="User Doesn't exist")

    await update_user_profile(userId=user.userId, update=update.model_dump(exclude_none=True))
