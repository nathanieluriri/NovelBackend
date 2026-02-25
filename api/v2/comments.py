from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from schemas.admin_schema import ChapterInteractionUserOut
from schemas.comments_schema import CommentOut, InteractionTargetType
from schemas.listing_schema import PaginatedListOut
from security.auth import verify_admin_token, verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
from services.comments_services import (
    retrieve_chapter_comment_users,
    retrieve_chapter_comment_users_count,
    retrieve_target_comments,
    retrieve_target_comments_count,
    retrieve_user_comments,
    retrieve_user_comments_count,
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


@router.get("/get", response_model=PaginatedListOut[CommentOut], dependencies=[Depends(verify_any_token)])
async def get_comments_v2(
    targetType: Optional[InteractionTargetType] = None,
    targetId: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    dep=Depends(verify_any_token),
):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)

    if targetType is not None or targetId is not None:
        if targetType is None or targetId is None:
            raise HTTPException(status_code=400, detail="targetType and targetId must be provided together")
        items = await retrieve_target_comments(
            targetType=targetType,
            targetId=targetId,
            skip=skip,
            limit=safe_limit,
        )
        total = await retrieve_target_comments_count(targetType=targetType, targetId=targetId)
        return build_list_payload(items, skip=skip, limit=safe_limit, total=total)

    user_id = await _get_actor_user_id(dep)
    items = await retrieve_user_comments(userId=user_id, skip=skip, limit=safe_limit)
    total = await retrieve_user_comments_count(userId=user_id)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get("/get/target/{targetType}/{targetId}", response_model=PaginatedListOut[CommentOut])
async def get_target_comments_v2(
    targetType: InteractionTargetType,
    targetId: str,
    skip: int = 0,
    limit: int = 20,
):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await retrieve_target_comments(
        targetType=targetType,
        targetId=targetId,
        skip=skip,
        limit=safe_limit,
    )
    total = await retrieve_target_comments_count(targetType=targetType, targetId=targetId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get("/get/{chapterId}", response_model=PaginatedListOut[CommentOut])
async def get_chapter_comments_v2(chapterId: str, skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await retrieve_target_comments(
        targetType=InteractionTargetType.chapter,
        targetId=chapterId,
        skip=skip,
        limit=safe_limit,
    )
    total = await retrieve_target_comments_count(
        targetType=InteractionTargetType.chapter,
        targetId=chapterId,
    )
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get(
    "/admin/get/chapter/{chapterId}/users",
    response_model=PaginatedListOut[ChapterInteractionUserOut],
    dependencies=[Depends(verify_admin_token)],
)
async def get_chapter_comment_users_v2(chapterId: str, skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await retrieve_chapter_comment_users(chapterId=chapterId, skip=skip, limit=safe_limit)
    total = await retrieve_chapter_comment_users_count(chapterId=chapterId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)
