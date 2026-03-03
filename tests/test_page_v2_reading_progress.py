import asyncio
from types import SimpleNamespace

from fastapi import BackgroundTasks

from api.v2 import page as page_v2


PAGE_ID = "a" * 24
CHAPTER_ID = "b" * 24
USER_ID = "c" * 24


def test_get_particular_page_v2_tracks_reading_progress_for_member(monkeypatch):
    async def fake_resolve_reader(*args, **kwargs):
        return "member", SimpleNamespace(userId=USER_ID)

    async def fake_fetch_single_page_by_page_id_for_user(*args, **kwargs):
        return SimpleNamespace(chapterId=CHAPTER_ID)

    monkeypatch.setattr(page_v2, "_resolve_reader", fake_resolve_reader)
    monkeypatch.setattr(page_v2, "fetch_single_page_by_pageId_for_user", fake_fetch_single_page_by_page_id_for_user)

    background_tasks = BackgroundTasks()
    page = asyncio.run(
        page_v2.get_particular_page_v2(
            pageId=PAGE_ID,
            background_tasks=background_tasks,
            dep={"accessToken": "token", "role": "member"},
        )
    )

    assert page.chapterId == CHAPTER_ID
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is page_v2.track_user_reading_progress
    assert background_tasks.tasks[0].args == (USER_ID, CHAPTER_ID, PAGE_ID)


def test_get_particular_page_v2_does_not_track_for_admin(monkeypatch):
    async def fake_resolve_reader(*args, **kwargs):
        return "admin", SimpleNamespace(userId=USER_ID)

    async def fake_fetch_single_page_by_page_id(*args, **kwargs):
        return SimpleNamespace(chapterId=CHAPTER_ID)

    monkeypatch.setattr(page_v2, "_resolve_reader", fake_resolve_reader)
    monkeypatch.setattr(page_v2, "fetch_single_page_by_pageId", fake_fetch_single_page_by_page_id)

    background_tasks = BackgroundTasks()
    page = asyncio.run(
        page_v2.get_particular_page_v2(
            pageId=PAGE_ID,
            background_tasks=background_tasks,
            dep={"accessToken": "token", "role": "admin"},
        )
    )

    assert page.chapterId == CHAPTER_ID
    assert background_tasks.tasks == []


def test_get_all_available_pages_v2_tracks_reading_progress_for_member(monkeypatch):
    async def fake_resolve_reader(*args, **kwargs):
        return "member", SimpleNamespace(userId=USER_ID)

    async def fake_fetch_page_for_user(*args, **kwargs):
        return [SimpleNamespace(id=PAGE_ID, chapterId=CHAPTER_ID)]

    async def fake_fetch_pages_count(*args, **kwargs):
        return 1

    monkeypatch.setattr(page_v2, "_resolve_reader", fake_resolve_reader)
    monkeypatch.setattr(page_v2, "fetch_page_for_user", fake_fetch_page_for_user)
    monkeypatch.setattr(page_v2, "fetch_pages_count", fake_fetch_pages_count)

    background_tasks = BackgroundTasks()
    payload = asyncio.run(
        page_v2.get_all_available_pages_v2(
            chapterId=CHAPTER_ID,
            background_tasks=background_tasks,
            skip=0,
            limit=20,
            dep={"accessToken": "token", "role": "member"},
        )
    )

    assert payload.meta.total == 1
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is page_v2.track_user_reading_progress
    assert background_tasks.tasks[0].args == (USER_ID, CHAPTER_ID, PAGE_ID)


def test_get_all_available_pages_v2_does_not_track_for_admin(monkeypatch):
    async def fake_resolve_reader(*args, **kwargs):
        return "admin", SimpleNamespace(userId=USER_ID)

    async def fake_fetch_page(*args, **kwargs):
        return [SimpleNamespace(id=PAGE_ID, chapterId=CHAPTER_ID)]

    async def fake_fetch_pages_count(*args, **kwargs):
        return 1

    monkeypatch.setattr(page_v2, "_resolve_reader", fake_resolve_reader)
    monkeypatch.setattr(page_v2, "fetch_page", fake_fetch_page)
    monkeypatch.setattr(page_v2, "fetch_pages_count", fake_fetch_pages_count)

    background_tasks = BackgroundTasks()
    payload = asyncio.run(
        page_v2.get_all_available_pages_v2(
            chapterId=CHAPTER_ID,
            background_tasks=background_tasks,
            skip=0,
            limit=20,
            dep={"accessToken": "token", "role": "admin"},
        )
    )

    assert payload.meta.total == 1
    assert background_tasks.tasks == []
