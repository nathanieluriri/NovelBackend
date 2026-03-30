import asyncio

import pytest
from fastapi import HTTPException

from services import reading_progress_service
from schemas.reading_progress_schema import ReadingProgressOut
from schemas.user_schema import UserOut


USER_ID = "a" * 24
CHAPTER_ID = "b" * 24
PAGE_ID = "c" * 24
OTHER_CHAPTER_ID = "d" * 24


def _user() -> UserOut:
    return UserOut.model_validate({"_id": USER_ID, "email": "reader@example.com"})


def test_get_user_reading_progress_returns_progress_when_record_is_valid(monkeypatch):
    async def fake_get_reading_progress(*args, **kwargs):
        return {"userId": USER_ID, "chapterId": CHAPTER_ID, "pageId": PAGE_ID, "dateUpdated": "2026-03-01T10:00:00+00:00"}

    async def fake_get_chapter_by_chapter_id(*args, **kwargs):
        return {"_id": CHAPTER_ID, "bookId": "e" * 24, "chapterLabel": "Chapter 1", "number": 1, "accessType": "free"}

    async def fake_get_page_by_page_id(*args, **kwargs):
        return {"_id": PAGE_ID, "chapterId": CHAPTER_ID}

    async def fake_get_chapter_summary(*args, **kwargs):
        return {"id": CHAPTER_ID}

    async def fake_get_page_summary(*args, **kwargs):
        return {"id": PAGE_ID}

    async def fake_model_async_validate(self):
        return self

    monkeypatch.setattr(reading_progress_service, "get_reading_progress", fake_get_reading_progress)
    monkeypatch.setattr(reading_progress_service, "get_chapter_by_chapter_id", fake_get_chapter_by_chapter_id)
    monkeypatch.setattr(reading_progress_service, "get_page_by_page_id", fake_get_page_by_page_id)
    monkeypatch.setattr(reading_progress_service, "get_chapter_summary", fake_get_chapter_summary)
    monkeypatch.setattr(reading_progress_service, "get_page_summary", fake_get_page_summary)
    monkeypatch.setattr(reading_progress_service.ChapterOut, "model_async_validate", fake_model_async_validate)

    progress = asyncio.run(reading_progress_service.get_user_reading_progress(_user()))

    assert isinstance(progress, ReadingProgressOut)
    assert progress.chapterId == CHAPTER_ID
    assert progress.pageId == PAGE_ID


def test_get_user_reading_progress_returns_missing_when_page_is_stale(monkeypatch):
    async def fake_get_reading_progress(*args, **kwargs):
        return {"userId": USER_ID, "chapterId": CHAPTER_ID, "pageId": PAGE_ID}

    async def fake_get_chapter_by_chapter_id(*args, **kwargs):
        return {"_id": CHAPTER_ID, "bookId": "e" * 24, "chapterLabel": "Chapter 1", "number": 1, "accessType": "free"}

    async def fake_get_page_by_page_id(*args, **kwargs):
        return {"_id": PAGE_ID, "chapterId": OTHER_CHAPTER_ID}

    monkeypatch.setattr(reading_progress_service, "get_reading_progress", fake_get_reading_progress)
    monkeypatch.setattr(reading_progress_service, "get_chapter_by_chapter_id", fake_get_chapter_by_chapter_id)
    monkeypatch.setattr(reading_progress_service, "get_page_by_page_id", fake_get_page_by_page_id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(reading_progress_service.get_user_reading_progress(_user()))

    assert exc.value.status_code == 404
    assert exc.value.detail == "No stopped-reading information found"
