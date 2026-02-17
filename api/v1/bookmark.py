from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from schemas.bookmark_schema import BookMarkCreateRequest, BookMarkOutAsync, InteractionTargetType
from security.auth import verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
from services.bookmark_services import create_bookmark_for_target, remove_bookmark_for_user, retrieve_user_bookmark
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


@router.get("/get", response_model=List[BookMarkOutAsync], dependencies=[Depends(verify_any_token)])
async def get_all_available_bookmarks(
    targetType: Optional[InteractionTargetType] = None,
    skip: int = 0,
    limit: int = 20,
    dep=Depends(verify_any_token),
):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = min(max(limit, 1), 100)
    user_id = await _get_actor_user_id(dep)
    return await retrieve_user_bookmark(
        userId=user_id,
        targetType=targetType,
        skip=skip,
        limit=safe_limit,
    )


# Legacy wrapper: returns only caller data, regardless of provided path userId.
@router.get("/get/{userId}", response_model=List[BookMarkOutAsync], dependencies=[Depends(verify_any_token)])
async def get_all_available_bookmarks_legacy(userId: str, dep=Depends(verify_any_token)):
    caller_id = await _get_actor_user_id(dep)
    if userId != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized to view another user's bookmarks")
    return await retrieve_user_bookmark(userId=caller_id)


@router.post("/create", response_model=BookMarkOutAsync, dependencies=[Depends(verify_any_token)])
async def create_new_bookmark(bookmark: BookMarkCreateRequest, dep=Depends(verify_any_token)):
    user_id = await _get_actor_user_id(dep)
    return await create_bookmark_for_target(userId=user_id, request=bookmark)


@router.delete("/remove/{bookmarkId}", response_model=BookMarkOutAsync, dependencies=[Depends(verify_any_token)])
async def delete_a_bookmark(bookmarkId: str, dep=Depends(verify_any_token)):
    user_id = await _get_actor_user_id(dep)
    removed = await remove_bookmark_for_user(bookmarkId=bookmarkId, userId=user_id)
    if removed is None:
        raise HTTPException(status_code=404, detail="Resource already deleted")
    return removed
