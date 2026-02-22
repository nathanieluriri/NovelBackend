from fastapi import APIRouter, Depends, HTTPException

from schemas.chapter_schema import ChapterOut
from schemas.listing_schema import PaginatedListOut
from security.auth import verify_admin_token, verify_any_token
from services.chapter_services import fetch_chapters, fetch_chapters_count
from services.listing_service import build_list_payload, clamp_limit

router = APIRouter()


@router.get(
    "/admin/get/allChapters/{bookId}",
    response_model=PaginatedListOut[ChapterOut],
    dependencies=[Depends(verify_admin_token)],
)
async def get_all_available_chapters_admin_v2(bookId: str, skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await fetch_chapters(bookId=bookId, start=skip, stop=skip + safe_limit)
    total = await fetch_chapters_count(bookId=bookId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get(
    "/user/get/allChapters/{bookId}",
    response_model=PaginatedListOut[ChapterOut],
    dependencies=[Depends(verify_any_token)],
)
async def get_all_available_chapters_user_v2(bookId: str, skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await fetch_chapters(bookId=bookId, start=skip, stop=skip + safe_limit)
    total = await fetch_chapters_count(bookId=bookId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)
