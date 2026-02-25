from fastapi import APIRouter, Depends, HTTPException

from schemas.admin_schema import ChapterInteractionUserOut
from schemas.likes_schema import LikeOut
from schemas.listing_schema import PaginatedListOut
from security.auth import verify_admin_token, verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
from services.like_services import (
    retrieve_chapter_like_users,
    retrieve_chapter_like_users_count,
    retrieve_chapter_likes,
    retrieve_chapter_likes_count,
    retrieve_user_likes,
    retrieve_user_likes_count,
)
from services.listing_service import build_list_payload, clamp_limit
from services.user_service import get_user_details_with_accessToken

router = APIRouter()


async def _get_actor_user_id(dep: dict) -> str:
    if dep["role"] == "member":
        user = await get_user_details_with_accessToken(token=dep["accessToken"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.userId

    admin = await get_admin_details_with_accessToken_service(token=dep["accessToken"])
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid token")
    return admin.userId


@router.get("/get", response_model=PaginatedListOut[LikeOut], dependencies=[Depends(verify_any_token)])
async def get_user_likes_v2(skip: int = 0, limit: int = 20, dep=Depends(verify_any_token)):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    user_id = await _get_actor_user_id(dep)
    items = await retrieve_user_likes(userId=user_id, skip=skip, limit=safe_limit)
    total = await retrieve_user_likes_count(userId=user_id)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get("/get/{chapterId}", response_model=PaginatedListOut[LikeOut])
async def get_chapter_likes_v2(chapterId: str, skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await retrieve_chapter_likes(chapterId=chapterId, skip=skip, limit=safe_limit)
    total = await retrieve_chapter_likes_count(chapterId=chapterId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get(
    "/admin/get/chapter/{chapterId}/users",
    response_model=PaginatedListOut[ChapterInteractionUserOut],
    dependencies=[Depends(verify_admin_token)],
)
async def get_chapter_like_users_v2(chapterId: str, skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await retrieve_chapter_like_users(chapterId=chapterId, skip=skip, limit=safe_limit)
    total = await retrieve_chapter_like_users_count(chapterId=chapterId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)
