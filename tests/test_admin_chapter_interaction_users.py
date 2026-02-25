import asyncio

import pytest
from fastapi import HTTPException

from services import comments_services, like_services


CHAPTER_ID = "a" * 24
USER_A = "b" * 24
USER_B = "c" * 24


def test_retrieve_chapter_like_users_returns_unique_users_with_meta(monkeypatch):
    async def fake_fetch_chapter_with_chapter_id(*args, **kwargs):
        return {"_id": CHAPTER_ID}

    async def fake_get_chapter_like_user_stats(*args, **kwargs):
        return [
            {
                "_id": USER_A,
                "interactionCount": 2,
                "lastInteractionAt": "2026-02-01T12:00:00+00:00",
            },
            {
                "_id": USER_B,
                "interactionCount": 1,
                "lastInteractionAt": 1731182400,
            },
        ]

    async def fake_get_users_by_user_ids(*args, **kwargs):
        return [
            {
                "_id": USER_A,
                "firstName": "Ada",
                "lastName": "Lovelace",
                "email": "ada@example.com",
                "avatar": "https://example.com/ada.jpg",
            }
        ]

    monkeypatch.setattr(like_services, "fetch_chapter_with_chapterId", fake_fetch_chapter_with_chapter_id)
    monkeypatch.setattr(like_services, "get_chapter_like_user_stats", fake_get_chapter_like_user_stats)
    monkeypatch.setattr(like_services, "get_users_by_user_ids", fake_get_users_by_user_ids)

    users = asyncio.run(like_services.retrieve_chapter_like_users(chapterId=CHAPTER_ID, skip=0, limit=20))

    assert len(users) == 2
    assert users[0].userId == USER_A
    assert users[0].interactionCount == 2
    assert users[0].firstName == "Ada"
    assert users[1].userId == USER_B
    assert users[1].interactionCount == 1
    assert users[1].email is None
    assert users[1].lastInteractionAt.endswith("+00:00")


def test_retrieve_chapter_like_users_count_checks_chapter_exists(monkeypatch):
    async def fake_fetch_chapter_with_chapter_id(*args, **kwargs):
        return None

    monkeypatch.setattr(like_services, "fetch_chapter_with_chapterId", fake_fetch_chapter_with_chapter_id)

    with pytest.raises(HTTPException) as err:
        asyncio.run(like_services.retrieve_chapter_like_users_count(chapterId=CHAPTER_ID))

    assert err.value.status_code == 404


def test_retrieve_chapter_comment_users_returns_unique_users_with_meta(monkeypatch):
    async def fake_get_chapter_by_chapter_id(*args, **kwargs):
        return {"_id": CHAPTER_ID}

    async def fake_get_chapter_comment_user_stats(*args, **kwargs):
        return [
            {
                "_id": USER_A,
                "interactionCount": 4,
                "lastInteractionAt": "2026-01-30T08:30:00+00:00",
            }
        ]

    async def fake_get_users_by_user_ids(*args, **kwargs):
        return [
            {
                "_id": USER_A,
                "firstName": "Grace",
                "lastName": "Hopper",
                "email": "grace@example.com",
            }
        ]

    monkeypatch.setattr(comments_services, "get_chapter_by_chapter_id", fake_get_chapter_by_chapter_id)
    monkeypatch.setattr(comments_services, "get_chapter_comment_user_stats", fake_get_chapter_comment_user_stats)
    monkeypatch.setattr(comments_services, "get_users_by_user_ids", fake_get_users_by_user_ids)

    users = asyncio.run(comments_services.retrieve_chapter_comment_users(chapterId=CHAPTER_ID, skip=0, limit=20))

    assert len(users) == 1
    assert users[0].userId == USER_A
    assert users[0].firstName == "Grace"
    assert users[0].interactionCount == 4


def test_retrieve_chapter_comment_users_count(monkeypatch):
    async def fake_get_chapter_by_chapter_id(*args, **kwargs):
        return {"_id": CHAPTER_ID}

    async def fake_count_chapter_comment_users(*args, **kwargs):
        return 9

    monkeypatch.setattr(comments_services, "get_chapter_by_chapter_id", fake_get_chapter_by_chapter_id)
    monkeypatch.setattr(comments_services, "count_chapter_comment_users", fake_count_chapter_comment_users)

    count = asyncio.run(comments_services.retrieve_chapter_comment_users_count(chapterId=CHAPTER_ID))

    assert count == 9
