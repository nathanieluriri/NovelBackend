from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from schemas.listing_schema import PaginatedListOut
from schemas.page_schema import PageOut
from security.auth import verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
from services.listing_service import build_list_payload, clamp_limit
from services.page_services import (
    fetch_page,
    fetch_page_for_user,
    fetch_pages_count,
    fetch_single_page_by_pageId,
    fetch_single_page_by_pageId_for_user,
)
from services.reading_progress_service import track_user_reading_progress
from services.user_service import get_user_details_with_accessToken

router = APIRouter()


async def _resolve_reader(dep: dict):
    role = dep.get("role")
    access_token = dep.get("accessToken")
    if not access_token:
        raise HTTPException(status_code=401, detail="Invalid token")

    if role == "member":
        user = await get_user_details_with_accessToken(token=access_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return role, user

    if role == "admin":
        admin = await get_admin_details_with_accessToken_service(token=access_token)
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid token")
        return role, admin

    raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/get/{chapterId}", response_model=PaginatedListOut[PageOut])
async def get_all_available_pages_v2(
    chapterId: str,
    background_tasks: BackgroundTasks,
    skip: int = 0,
    limit: int = 20,
    dep=Depends(verify_any_token),
):
    if len(chapterId) != 24:
        raise HTTPException(status_code=400, detail="chapterId must be exactly 24 characters long")
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)

    role, reader = await _resolve_reader(dep)
    if role == "admin":
        items = await fetch_page(chapterId=chapterId, skip=skip, limit=safe_limit)
    else:
        items = await fetch_page_for_user(chapterId=chapterId, user=reader, skip=skip, limit=safe_limit)
        first_page = items[0] if items else None
        if first_page and reader.userId and first_page.id and first_page.chapterId:
            background_tasks.add_task(
                track_user_reading_progress,
                reader.userId,
                first_page.chapterId,
                first_page.id,
            )
    total = await fetch_pages_count(chapterId=chapterId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get("/get/page/{pageId}", response_model=PageOut)
async def get_particular_page_v2(
    pageId: str,
    background_tasks: BackgroundTasks,
    dep=Depends(verify_any_token),
):
    if len(pageId) != 24:
        raise HTTPException(status_code=400, detail="pageId must be exactly 24 characters long")

    role, reader = await _resolve_reader(dep)
    if role == "admin":
        return await fetch_single_page_by_pageId(pageId=pageId)

    page = await fetch_single_page_by_pageId_for_user(pageId=pageId, user=reader)
    if reader.userId and page.chapterId:
        background_tasks.add_task(
            track_user_reading_progress,
            reader.userId,
            page.chapterId,
            pageId,
        )
    return page
