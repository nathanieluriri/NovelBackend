from fastapi import APIRouter, Depends, HTTPException

from schemas.reading_progress_schema import ReadingProgressOut
from schemas.user_v2_schema import (
    IndexedBookmarkOut,
    IndexedLikeOut,
    InteractionTotals,
    ListMeta,
    UserBookmarksListOut,
    UserDetailsV2Out,
    UserLikesListOut,
)
from security.auth import verify_token
from services.bookmark_services import retrieve_user_bookmark, retrieve_user_bookmark_count
from services.like_services import retrieve_user_likes, retrieve_user_likes_count
from services.reading_progress_service import get_user_reading_progress
from services.user_service import get_user_details_with_accessToken

router = APIRouter()


def _sanitize_limit(limit: int) -> int:
    return min(max(limit, 1), 100)


def _build_meta(skip: int, limit: int, returned: int, total: int) -> ListMeta:
    has_more = skip + returned < total
    return ListMeta(
        skip=skip,
        limit=limit,
        returned=returned,
        total=total,
        hasMore=has_more,
    )


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
        likesMeta=_build_meta(skip=0, limit=100, returned=len(likes_indexed), total=likes_total),
        bookmarksMeta=_build_meta(skip=0, limit=100, returned=len(bookmarks_indexed), total=bookmarks_total),
    )


@router.get("/likes", response_model=UserLikesListOut)
async def get_user_likes_v2(skip: int = 0, limit: int = 20, dep=Depends(verify_token)):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = _sanitize_limit(limit)
    user = await _get_user_or_401(dep)
    if not user.userId:
        raise HTTPException(status_code=401, detail="Invalid token")

    likes_total = await retrieve_user_likes_count(user.userId)
    likes = await retrieve_user_likes(user.userId, skip=skip, limit=safe_limit)
    items = [IndexedLikeOut(index=skip + i + 1, item=item) for i, item in enumerate(likes)]
    return UserLikesListOut(
        items=items,
        meta=_build_meta(skip=skip, limit=safe_limit, returned=len(items), total=likes_total),
    )


@router.get("/bookmarks", response_model=UserBookmarksListOut)
async def get_user_bookmarks_v2(skip: int = 0, limit: int = 20, dep=Depends(verify_token)):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = _sanitize_limit(limit)
    user = await _get_user_or_401(dep)
    if not user.userId:
        raise HTTPException(status_code=401, detail="Invalid token")

    bookmarks_total = await retrieve_user_bookmark_count(user.userId)
    bookmarks = await retrieve_user_bookmark(user.userId, skip=skip, limit=safe_limit)
    items = [IndexedBookmarkOut(index=skip + i + 1, item=item) for i, item in enumerate(bookmarks)]
    return UserBookmarksListOut(
        items=items,
        meta=_build_meta(skip=skip, limit=safe_limit, returned=len(items), total=bookmarks_total),
    )


@router.get("/reading/progress", response_model=ReadingProgressOut, response_model_exclude_none=True)
async def get_stopped_reading_progress_v2(dep=Depends(verify_token)):
    user = await _get_user_or_401(dep)
    return await get_user_reading_progress(user=user)
