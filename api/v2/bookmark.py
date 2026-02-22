from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from schemas.bookmark_schema import BookMarkOutAsync, InteractionTargetType
from schemas.listing_schema import PaginatedListOut
from security.auth import verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
from services.bookmark_services import retrieve_user_bookmark, retrieve_user_bookmark_count
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


@router.get("/get", response_model=PaginatedListOut[BookMarkOutAsync], dependencies=[Depends(verify_any_token)])
async def get_bookmarks_v2(
    targetType: Optional[InteractionTargetType] = None,
    skip: int = 0,
    limit: int = 20,
    dep=Depends(verify_any_token),
):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    user_id = await _get_actor_user_id(dep)
    items = await retrieve_user_bookmark(
        userId=user_id,
        targetType=targetType,
        skip=skip,
        limit=safe_limit,
    )
    total = await retrieve_user_bookmark_count(userId=user_id, targetType=targetType)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get("/get/{userId}", response_model=PaginatedListOut[BookMarkOutAsync], dependencies=[Depends(verify_any_token)])
async def get_bookmarks_legacy_v2(
    userId: str,
    targetType: Optional[InteractionTargetType] = None,
    skip: int = 0,
    limit: int = 20,
    dep=Depends(verify_any_token),
):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    caller_id = await _get_actor_user_id(dep)
    if caller_id != userId:
        raise HTTPException(status_code=403, detail="Not authorized to view another user's bookmarks")
    items = await retrieve_user_bookmark(
        userId=caller_id,
        targetType=targetType,
        skip=skip,
        limit=safe_limit,
    )
    total = await retrieve_user_bookmark_count(userId=caller_id, targetType=targetType)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)
