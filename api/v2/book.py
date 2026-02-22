from fastapi import APIRouter, HTTPException

from schemas.book_schema import BookOut
from schemas.listing_schema import PaginatedListOut
from services.book_services import fetch_books_count, fetch_books_paginated
from services.listing_service import build_list_payload, clamp_limit

router = APIRouter()


@router.get("/get", response_model=PaginatedListOut[BookOut])
async def get_books_v2(skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await fetch_books_paginated(skip=skip, limit=safe_limit)
    total = await fetch_books_count()
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)
