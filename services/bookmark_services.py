from typing import List

from fastapi import HTTPException

from repositories.book_repo import get_book_by_book_id
from repositories.bookmark_repo import (
    count_user_bookmarks,
    create_bookmark,
    delete_bookmark_by_id_userId,
    delete_bookmarks_with_bookmark_id,
    get_all_user_bookmarks,
    get_bookmark_by_user_target,
)
from repositories.chapter_repo import get_chapter_by_chapter_id
from repositories.page_repo import get_page_by_page_id
from schemas.bookmark_schema import (
    BookMarkCreate,
    BookMarkCreateRequest,
    BookMarkOutAsync,
    InteractionTargetType,
)
from services.chapter_services import fetch_chapter_with_chapterId
from core.entity_cache import get_chapter_summary


async def _build_bookmark_model(userId: str, targetType: InteractionTargetType, targetId: str) -> BookMarkCreate:
    if targetType == InteractionTargetType.book:
        book = await get_book_by_book_id(targetId)
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookMarkCreate(userId=userId, targetType=targetType, targetId=targetId)

    if targetType == InteractionTargetType.chapter:
        chapter = await get_chapter_by_chapter_id(targetId)
        if chapter is None:
            raise HTTPException(status_code=404, detail="Chapter not found")
        chapter_label = chapter.get("chapterLabel")
        return BookMarkCreate(
            userId=userId,
            targetType=targetType,
            targetId=targetId,
            chapterId=targetId,
            chapterLabel=chapter_label,
        )

    page = await get_page_by_page_id(targetId)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    chapter_data = await fetch_chapter_with_chapterId(chapterId=page["chapterId"])
    chapter_label = chapter_data.chapterLabel if chapter_data else None
    return BookMarkCreate(
        userId=userId,
        targetType=targetType,
        targetId=targetId,
        pageId=targetId,
        chapterId=page.get("chapterId"),
        chapterLabel=chapter_label,
    )


async def create_bookmark_for_target(userId: str, request: BookMarkCreateRequest) -> BookMarkOutAsync:
    if request.targetType is None or request.targetId is None:
        raise HTTPException(status_code=422, detail="targetType and targetId are required")
    existing = await get_bookmark_by_user_target(userId=userId, targetType=request.targetType, targetId=request.targetId)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Bookmark already exists")

    bookmark_model = await _build_bookmark_model(
        userId=userId,
        targetType=request.targetType,
        targetId=request.targetId,
    )
    created = await create_bookmark(bookmark_data=bookmark_model)
    result = BookMarkOutAsync(**created)
    if result.chapterId:
        result.chapterSummary = await get_chapter_summary(result.chapterId)
    return result


async def remove_bookmark_for_user(bookmarkId: str, userId: str) -> BookMarkOutAsync | None:
    removed = await delete_bookmark_by_id_userId(bookmarkId=bookmarkId, userId=userId)
    if removed is None:
        return None
    result = BookMarkOutAsync(**removed)
    if result.chapterId:
        result.chapterSummary = await get_chapter_summary(result.chapterId)
    return result


async def remove_bookmark(bookmarkId: str) -> BookMarkOutAsync | None:
    removed = await delete_bookmarks_with_bookmark_id(bookmarkId=bookmarkId)
    if removed is None:
        return None
    result = BookMarkOutAsync(**removed)
    if result.chapterId:
        result.chapterSummary = await get_chapter_summary(result.chapterId)
    return result


async def retrieve_user_bookmark(
    userId: str,
    targetType: InteractionTargetType | None = None,
    skip: int = 0,
    limit: int = 20,
) -> List[BookMarkOutAsync]:
    bookmarks = await get_all_user_bookmarks(
        userId=userId,
        targetType=targetType,
        skip=skip,
        limit=limit,
    )
    results = [BookMarkOutAsync(**bookmark) for bookmark in bookmarks]
    for item in results:
        if item.chapterId:
            item.chapterSummary = await get_chapter_summary(item.chapterId)
    return results


# Compatibility wrapper.
async def add_bookmark(userId: str, pageId: str):
    request = BookMarkCreateRequest(targetType=InteractionTargetType.page, targetId=pageId)
    return await create_bookmark_for_target(userId=userId, request=request)


async def retrieve_user_bookmark_count(
    userId: str,
    targetType: InteractionTargetType | None = None,
) -> int:
    return await count_user_bookmarks(userId=userId, targetType=targetType)
