import asyncio

from schemas.likes_schema import LikeWithUserOut
from services import like_services
from api.v2 import like as like_v2


CHAPTER_ID = "a" * 24
USER_A = "b" * 24
USER_B = "c" * 24


def test_retrieve_chapter_likes_with_user_details_hydrates_and_falls_back(monkeypatch):
    async def fake_get_all_chapter_likes(*args, **kwargs):
        return [
            {
                "_id": "d" * 24,
                "userId": USER_A,
                "role": "member",
                "chapterId": CHAPTER_ID,
                "chapaterLabel": "Chapter 1",
                "dateCreated": "2026-03-01T10:00:00+00:00",
            },
            {
                "_id": "e" * 24,
                "userId": USER_B,
                "role": "member",
                "chapterId": CHAPTER_ID,
                "chapaterLabel": "Chapter 1",
                "dateCreated": "2026-03-01T11:00:00+00:00",
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

    async def fake_get_chapter_summary(*args, **kwargs):
        return {"chapterId": CHAPTER_ID}

    monkeypatch.setattr(like_services, "get_all_chapter_likes", fake_get_all_chapter_likes)
    monkeypatch.setattr(like_services, "get_users_by_user_ids", fake_get_users_by_user_ids)
    monkeypatch.setattr(like_services, "get_chapter_summary", fake_get_chapter_summary)

    likes = asyncio.run(like_services.retrieve_chapter_likes_with_user_details(chapterId=CHAPTER_ID, skip=0, limit=20))

    assert len(likes) == 2
    assert likes[0].user is not None
    assert likes[0].user.firstName == "Ada"
    assert likes[0].user.email == "ada@example.com"
    assert likes[1].user is None
    assert likes[0].chapterSummary is not None
    if isinstance(likes[0].chapterSummary, dict):
        assert likes[0].chapterSummary["chapterId"] == CHAPTER_ID


def test_retrieve_chapter_likes_with_user_details_deduplicates_user_fetch(monkeypatch):
    captured_user_ids = {}

    async def fake_get_all_chapter_likes(*args, **kwargs):
        return [
            {
                "_id": "f" * 24,
                "userId": USER_A,
                "role": "member",
                "chapterId": CHAPTER_ID,
                "chapaterLabel": "Chapter 2",
                "dateCreated": "2026-03-01T10:00:00+00:00",
            },
            {
                "_id": "0" * 24,
                "userId": USER_A,
                "role": "member",
                "chapterId": CHAPTER_ID,
                "chapaterLabel": "Chapter 2",
                "dateCreated": "2026-03-01T11:00:00+00:00",
            },
        ]

    async def fake_get_users_by_user_ids(userIds):
        captured_user_ids["value"] = userIds
        return []

    async def fake_get_chapter_summary(*args, **kwargs):
        return {"chapterId": CHAPTER_ID}

    monkeypatch.setattr(like_services, "get_all_chapter_likes", fake_get_all_chapter_likes)
    monkeypatch.setattr(like_services, "get_users_by_user_ids", fake_get_users_by_user_ids)
    monkeypatch.setattr(like_services, "get_chapter_summary", fake_get_chapter_summary)

    asyncio.run(like_services.retrieve_chapter_likes_with_user_details(chapterId=CHAPTER_ID, skip=0, limit=20))

    assert captured_user_ids["value"] == [USER_A]


def test_get_chapter_likes_v2_uses_enriched_like_payload(monkeypatch):
    async def fake_retrieve_chapter_likes_with_user_details(*args, **kwargs):
        return [
            LikeWithUserOut(
                _id="1" * 24,
                userId=USER_A,
                role="member",
                chapterId=CHAPTER_ID,
                chapaterLabel="Chapter 1",
                dateCreated="2026-03-01T10:00:00+00:00",
                user={"firstName": "Ada"},
            )
        ]

    async def fake_retrieve_chapter_likes_count(*args, **kwargs):
        return 1

    monkeypatch.setattr(like_v2, "retrieve_chapter_likes_with_user_details", fake_retrieve_chapter_likes_with_user_details)
    monkeypatch.setattr(like_v2, "retrieve_chapter_likes_count", fake_retrieve_chapter_likes_count)

    payload = asyncio.run(like_v2.get_chapter_likes_v2(chapterId=CHAPTER_ID, skip=0, limit=20))

    assert payload.items[0].user is not None
    assert payload.items[0].user.firstName == "Ada"
    assert payload.meta.total == 1
