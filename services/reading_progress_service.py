from fastapi import HTTPException

from core.entity_cache import get_chapter_summary, get_page_summary
from repositories.chapter_repo import get_chapter_by_chapter_id
from repositories.reading_progress_repo import get_reading_progress, upsert_reading_progress
from schemas.chapter_schema import ChapterAccessType, ChapterOut
from schemas.reading_progress_schema import ReadingProgressOut, ReadingProgressRecord
from schemas.user_schema import UserOut
from services.access_service import is_chapter_unlocked, is_subscription_active


async def track_user_reading_progress(user_id: str, chapter_id: str, page_id: str) -> None:
    if not user_id or not chapter_id or not page_id:
        return
    await upsert_reading_progress(
        ReadingProgressRecord(
            userId=user_id,
            chapterId=chapter_id,
            pageId=page_id,
        )
    )


async def get_user_reading_progress(user: UserOut) -> ReadingProgressOut:
    if not user.userId:
        raise HTTPException(status_code=401, detail="User identity is missing")

    progress = await get_reading_progress(user_id=user.userId)
    if progress is None:
        raise HTTPException(status_code=404, detail="No stopped-reading information found")

    chapter = await get_chapter_by_chapter_id(chapterId=progress["chapterId"])
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter for stopped-reading information was not found")

    chapter_out = ChapterOut(**chapter)
    await chapter_out.model_async_validate()
    if not chapter_out.id:
        raise HTTPException(status_code=500, detail="Chapter identifier is missing")

    has_access = False
    access_type = chapter_out.accessType or ChapterAccessType.free
    if access_type == ChapterAccessType.free:
        has_access = True
    else:
        subscription = user.subscription.model_dump() if user.subscription else None
        if is_subscription_active(subscription):
            has_access = True
        elif await is_chapter_unlocked(user=user, chapter_id=chapter_out.id):
            has_access = True

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail=(
                "Cannot access stopped-reading info: subscription expired, "
                "chapter is not free, and chapter is not unlocked."
            ),
        )

    chapter_summary = await get_chapter_summary(progress["chapterId"])
    page_summary = await get_page_summary(progress["pageId"])
    return ReadingProgressOut(
        userId=user.userId,
        chapterId=progress["chapterId"],
        pageId=progress["pageId"],
        dateUpdated=progress.get("dateUpdated"),
        chapterSummary=chapter_summary,
        pageSummary=page_summary,
    )
