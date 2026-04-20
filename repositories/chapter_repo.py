import asyncio

from fastapi import HTTPException

from core.database import ASC, client, is_valid_id, maybe_id
from schemas.chapter_schema import ChapterCreate, ChapterUpdate, ChapterOut


CHAPTERS = "chapters"


_chapter_indexes_ready = False
_chapter_indexes_lock = asyncio.Lock()


async def ensure_chapter_indexes() -> None:
    """Indexes for the hot paths: lookups by bookId + ordering by number."""
    global _chapter_indexes_ready
    if _chapter_indexes_ready:
        return
    async with _chapter_indexes_lock:
        if _chapter_indexes_ready:
            return
        await client.ensure_index(
            CHAPTERS, [("bookId", ASC), ("number", ASC)], background=True
        )
        _chapter_indexes_ready = True


async def get_chapter_by_bookId(bookId: str, start: int = 0, stop: int = 100):
    if not is_valid_id(bookId):
        raise HTTPException(status_code=500, detail="Invalid Book Id")
    await ensure_chapter_indexes()
    return await client.find_many(
        CHAPTERS,
        {"bookId": bookId},
        skip=start,
        limit=stop - start,
    )


async def count_chapters_by_bookId(bookId: str) -> int:
    return await client.count(CHAPTERS, {"bookId": bookId})


async def get_chapter_by_chapter_id(chapterId: str) -> ChapterOut | None:
    oid = maybe_id(chapterId)
    if oid is None:
        return None
    return await client.find_one(CHAPTERS, {"_id": oid})


async def get_chapter_by_bookid_and_chapter_numer(bookId: str, chapterNumber: int):
    if not is_valid_id(bookId):
        return None
    await ensure_chapter_indexes()
    return await client.find_one(
        CHAPTERS, {"bookId": bookId, "number": chapterNumber}
    )


# Pure-Python helpers kept for callers that already fetched the list.
def get_chapter_by_number(number: int, chapters: list):
    matches = [c for c in chapters if c.get("number") == number]
    return matches[0] if matches else None


def get_chapter_by_chapterId(chapterId, chapters: list):
    matches = [c for c in chapters if c.get("_id") == chapterId]
    return matches[0] if matches else None


async def update_chapter_order_after_delete(deleted_position: int, bookId):
    return await client.update_many(
        CHAPTERS,
        {"bookId": bookId, "number": {"$gt": deleted_position}},
        {"inc": {"number": -1}},
    )


async def create_chapter(chapter_data: ChapterCreate):
    return await client.insert_and_fetch(CHAPTERS, chapter_data.model_dump())


async def update_chapter(chapter_id: str, update_data: ChapterUpdate):
    oid = maybe_id(chapter_id)
    if oid is None:
        return {"message": "Invalid chapter id."}

    update_dict = {
        k: v
        for k, v in update_data.model_dump(exclude_none=True).items()
        if v is not None
    }
    update_dict.pop("id", None)
    modified = await client.update_one(
        CHAPTERS, {"_id": oid}, {"set": update_dict}
    )
    if modified == 0:
        return {"message": "No changes made or chapter not found."}
    return await client.find_one(CHAPTERS, {"_id": oid})


async def delete_chapter_with_chapter_id(chapterId):
    oid = maybe_id(chapterId)
    if oid is None:
        return None
    return await client.find_one_and_delete(CHAPTERS, {"_id": oid})


async def delete_chapters_with_book_id(bookId: str):
    if not is_valid_id(bookId):
        return None
    return await client.delete_many(CHAPTERS, {"bookId": bookId})
