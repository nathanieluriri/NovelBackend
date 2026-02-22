from __future__ import annotations

import json
from typing import Any, Optional

from core.redis_cache import cache_db
from repositories.book_repo import get_book_by_book_id
from repositories.chapter_repo import get_chapter_by_chapter_id
from repositories.page_repo import get_page_by_page_id
from schemas.cache_summary_schema import BookSummaryOut, ChapterSummaryOut, PageSummaryOut
from schemas.utils import normalize_datetime_to_iso

CACHE_TTL_SECONDS = 900
SUMMARY_CACHE_VERSION = "v1"


def _build_key(entity_type: str, entity_id: str) -> str:
    return f"summary:{entity_type}:{entity_id}:{SUMMARY_CACHE_VERSION}"


def _safe_json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _safe_json_loads(raw: str) -> dict[str, Any] | None:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def _cache_get(key: str) -> dict[str, Any] | None:
    try:
        raw = cache_db.get(key)
    except Exception:
        return None
    if not raw:
        return None
    return _safe_json_loads(raw)


def _cache_set(key: str, payload: dict[str, Any]) -> None:
    try:
        cache_db.setex(key, CACHE_TTL_SECONDS, _safe_json_dumps(payload))
    except Exception:
        return


def _cache_delete(key: str) -> None:
    try:
        cache_db.delete(key)
    except Exception:
        return


def _extract_id(doc: dict[str, Any]) -> str:
    raw = doc.get("id", doc.get("_id"))
    return str(raw)


def _build_book_summary(doc: dict[str, Any]) -> BookSummaryOut:
    return BookSummaryOut(
        id=_extract_id(doc),
        name=doc.get("name"),
        number=doc.get("number"),
        chapterCount=doc.get("chapterCount"),
        dateCreated=normalize_datetime_to_iso(doc.get("dateCreated")),
        dateUpdated=normalize_datetime_to_iso(doc.get("dateUpdated")),
    )


def _build_chapter_summary(doc: dict[str, Any]) -> ChapterSummaryOut:
    return ChapterSummaryOut(
        id=_extract_id(doc),
        bookId=doc.get("bookId"),
        chapterLabel=doc.get("chapterLabel"),
        number=doc.get("number"),
        accessType=doc.get("accessType"),
        coverImage=doc.get("coverImage"),
        pageCount=doc.get("pageCount"),
        dateCreated=normalize_datetime_to_iso(doc.get("dateCreated")),
        dateUpdated=normalize_datetime_to_iso(doc.get("dateUpdated")),
    )


def _build_page_summary(doc: dict[str, Any]) -> PageSummaryOut:
    return PageSummaryOut(
        id=_extract_id(doc),
        chapterId=doc.get("chapterId"),
        status=doc.get("status"),
        number=doc.get("number"),
        textCount=doc.get("textCount"),
        dateCreated=normalize_datetime_to_iso(doc.get("dateCreated")),
        dateUpdated=normalize_datetime_to_iso(doc.get("dateUpdated")),
    )


async def get_book_summary(book_id: str) -> Optional[BookSummaryOut]:
    key = _build_key("book", book_id)
    cached = _cache_get(key)
    if cached:
        return BookSummaryOut.model_validate(cached)

    book = await get_book_by_book_id(bookId=book_id)
    if not book:
        return None
    summary = _build_book_summary(book)
    _cache_set(key, summary.model_dump(exclude_none=True))
    return summary


async def get_chapter_summary(chapter_id: str) -> Optional[ChapterSummaryOut]:
    key = _build_key("chapter", chapter_id)
    cached = _cache_get(key)
    if cached:
        return ChapterSummaryOut.model_validate(cached)

    chapter = await get_chapter_by_chapter_id(chapterId=chapter_id)
    if not chapter:
        return None
    summary = _build_chapter_summary(chapter)
    _cache_set(key, summary.model_dump(exclude_none=True))
    return summary


async def get_page_summary(page_id: str) -> Optional[PageSummaryOut]:
    key = _build_key("page", page_id)
    cached = _cache_get(key)
    if cached:
        return PageSummaryOut.model_validate(cached)

    page = await get_page_by_page_id(pageId=page_id)
    if not page:
        return None
    summary = _build_page_summary(page)
    _cache_set(key, summary.model_dump(exclude_none=True))
    return summary


async def invalidate_book_summary(book_id: str | None) -> None:
    if not book_id:
        return
    _cache_delete(_build_key("book", str(book_id)))


async def invalidate_chapter_summary(chapter_id: str | None) -> None:
    if not chapter_id:
        return
    _cache_delete(_build_key("chapter", str(chapter_id)))


async def invalidate_page_summary(page_id: str | None) -> None:
    if not page_id:
        return
    _cache_delete(_build_key("page", str(page_id)))
