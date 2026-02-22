from fastapi import APIRouter, Depends, HTTPException

from schemas.bookmark_schema import BookMarkOutAsync
from schemas.likes_schema import LikeOut
from schemas.listing_schema import PaginatedListOut
from schemas.reading_progress_schema import ReadingProgressOut
from schemas.user_v2_schema import (
    IndexedBookmarkOut,
    IndexedLikeOut,
    InteractionTotals,
    UserDetailsV2Out,
)
from security.auth import verify_token
from services.bookmark_services import retrieve_user_bookmark, retrieve_user_bookmark_count
from services.like_services import retrieve_user_likes, retrieve_user_likes_count
from services.listing_service import build_list_payload, build_meta, clamp_limit
from services.reading_progress_service import get_user_reading_progress
from services.user_service import get_user_details_with_accessToken

router = APIRouter()


async def _get_user_or_401(dep: dict):
    user = await get_user_details_with_accessToken(token=dep["accessToken"])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.get("/details", response_model=UserDetailsV2Out)
async def get_user_details_v2(dep=Depends(verify_token)):
    user = await _get_user_or_401(dep)
    if not user.userId:
        raise HTTPException(status_code=401, detail="Invalid token")

    likes_total = await retrieve_user_likes_count(user.userId)
    bookmarks_total = await retrieve_user_bookmark_count(user.userId)

    likes_preview = await retrieve_user_likes(user.userId, skip=0, limit=100)
    bookmarks_preview = await retrieve_user_bookmark(user.userId, skip=0, limit=100)

    likes_indexed = [IndexedLikeOut(index=i + 1, item=item) for i, item in enumerate(likes_preview)]
    bookmarks_indexed = [IndexedBookmarkOut(index=i + 1, item=item) for i, item in enumerate(bookmarks_preview)]

    return UserDetailsV2Out(
        summary=InteractionTotals(totalLikes=likes_total, totalBookmarks=bookmarks_total),
        likes=likes_indexed,
        bookmarks=bookmarks_indexed,
        likesMeta=build_meta(skip=0, limit=100, returned=len(likes_indexed), total=likes_total),
        bookmarksMeta=build_meta(skip=0, limit=100, returned=len(bookmarks_indexed), total=bookmarks_total),
    )


@router.get("/likes", response_model=PaginatedListOut[LikeOut])
async def get_user_likes_v2(skip: int = 0, limit: int = 20, dep=Depends(verify_token)):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    user = await _get_user_or_401(dep)
    if not user.userId:
        raise HTTPException(status_code=401, detail="Invalid token")

    likes_total = await retrieve_user_likes_count(user.userId)
    likes = await retrieve_user_likes(user.userId, skip=skip, limit=safe_limit)
    return build_list_payload(likes, skip=skip, limit=safe_limit, total=likes_total)


@router.get("/bookmarks", response_model=PaginatedListOut[BookMarkOutAsync])
async def get_user_bookmarks_v2(skip: int = 0, limit: int = 20, dep=Depends(verify_token)):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    user = await _get_user_or_401(dep)
    if not user.userId:
        raise HTTPException(status_code=401, detail="Invalid token")

    bookmarks_total = await retrieve_user_bookmark_count(user.userId)
    bookmarks = await retrieve_user_bookmark(user.userId, skip=skip, limit=safe_limit)
    return build_list_payload(bookmarks, skip=skip, limit=safe_limit, total=bookmarks_total)


@router.get("/reading/progress", response_model=ReadingProgressOut, response_model_exclude_none=True)
async def get_stopped_reading_progress_v2(dep=Depends(verify_token)):
    user = await _get_user_or_401(dep)
    return await get_user_reading_progress(user=user)
