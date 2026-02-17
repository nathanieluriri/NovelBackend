from typing import List

from fastapi import HTTPException

from repositories.book_repo import get_book_by_book_id
from repositories.bookmark_repo import (
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
    BookMarkOut,
    BookMarkOutAsync,
    InteractionTargetType,
)
from services.chapter_services import fetch_chapter_with_chapterId


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


async def create_bookmark_for_target(userId: str, request: BookMarkCreateRequest):
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
    return BookMarkOut(**created)


async def remove_bookmark_for_user(bookmarkId: str, userId: str):
    removed = await delete_bookmark_by_id_userId(bookmarkId=bookmarkId, userId=userId)
    if removed is None:
        return None
    return BookMarkOut(**removed)


async def remove_bookmark(bookmarkId: str):
    removed = await delete_bookmarks_with_bookmark_id(bookmarkId=bookmarkId)
    if removed is None:
        return None
    return BookMarkOut(**removed)


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
    return [BookMarkOutAsync(**bookmark) for bookmark in bookmarks]


# Compatibility wrapper.
async def add_bookmark(userId: str, pageId: str):
    request = BookMarkCreateRequest(targetType=InteractionTargetType.page, targetId=pageId)
    return await create_bookmark_for_target(userId=userId, request=request)
