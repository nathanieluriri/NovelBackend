from fastapi import APIRouter, Depends, HTTPException

from schemas.listing_schema import PaginatedListOut
from schemas.page_schema import PageOut
from security.auth import verify_any_token
from services.listing_service import build_list_payload, clamp_limit
from services.page_services import fetch_page_for_user, fetch_pages_count
from services.user_service import get_user_details_with_accessToken

router = APIRouter()


@router.get("/get/{chapterId}", response_model=PaginatedListOut[PageOut])
async def get_all_available_pages_v2(chapterId: str, skip: int = 0, limit: int = 20, dep=Depends(verify_any_token)):
    if len(chapterId) != 24:
        raise HTTPException(status_code=400, detail="chapterId must be exactly 24 characters long")
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)

    user_details = await get_user_details_with_accessToken(token=dep["accessToken"])
    if not user_details:
        raise HTTPException(status_code=401, detail="Invalid token")

    items = await fetch_page_for_user(chapterId=chapterId, user=user_details, skip=skip, limit=safe_limit)
    total = await fetch_pages_count(chapterId=chapterId)
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)
