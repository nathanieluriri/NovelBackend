import asyncio
from types import SimpleNamespace

from api.v2 import user as user_v2


USER_ID = "a" * 24


def test_get_user_details_v2_includes_profile_fields(monkeypatch):
    async def fake_get_user_or_401(*args, **kwargs):
        return SimpleNamespace(
            userId=USER_ID,
            email="reader@example.com",
            firstName="Reader",
            lastName="One",
            avatar="https://example.com/avatar.jpg",
        )

    async def fake_retrieve_user_likes_count(*args, **kwargs):
        return 2

    async def fake_retrieve_user_bookmark_count(*args, **kwargs):
        return 3

    async def fake_retrieve_user_likes(*args, **kwargs):
        return []

    async def fake_retrieve_user_bookmark(*args, **kwargs):
        return []

    monkeypatch.setattr(user_v2, "_get_user_or_401", fake_get_user_or_401)
    monkeypatch.setattr(user_v2, "retrieve_user_likes_count", fake_retrieve_user_likes_count)
    monkeypatch.setattr(user_v2, "retrieve_user_bookmark_count", fake_retrieve_user_bookmark_count)
    monkeypatch.setattr(user_v2, "retrieve_user_likes", fake_retrieve_user_likes)
    monkeypatch.setattr(user_v2, "retrieve_user_bookmark", fake_retrieve_user_bookmark)

    payload = asyncio.run(user_v2.get_user_details_v2(dep={"accessToken": "token"}))

    assert payload.userId == USER_ID
    assert payload.email == "reader@example.com"
    assert payload.firstName == "Reader"
    assert payload.lastName == "One"
    assert payload.avatar == "https://example.com/avatar.jpg"
    assert payload.summary.totalLikes == 2
    assert payload.summary.totalBookmarks == 3


def test_get_user_details_v2_allows_missing_optional_profile_fields(monkeypatch):
    async def fake_get_user_or_401(*args, **kwargs):
        return SimpleNamespace(
            userId=USER_ID,
            email="reader@example.com",
            firstName=None,
            lastName=None,
            avatar=None,
        )

    async def fake_retrieve_user_likes_count(*args, **kwargs):
        return 0

    async def fake_retrieve_user_bookmark_count(*args, **kwargs):
        return 0

    async def fake_retrieve_user_likes(*args, **kwargs):
        return []

    async def fake_retrieve_user_bookmark(*args, **kwargs):
        return []

    monkeypatch.setattr(user_v2, "_get_user_or_401", fake_get_user_or_401)
    monkeypatch.setattr(user_v2, "retrieve_user_likes_count", fake_retrieve_user_likes_count)
    monkeypatch.setattr(user_v2, "retrieve_user_bookmark_count", fake_retrieve_user_bookmark_count)
    monkeypatch.setattr(user_v2, "retrieve_user_likes", fake_retrieve_user_likes)
    monkeypatch.setattr(user_v2, "retrieve_user_bookmark", fake_retrieve_user_bookmark)

    payload = asyncio.run(user_v2.get_user_details_v2(dep={"accessToken": "token"}))

    assert payload.userId == USER_ID
    assert payload.email == "reader@example.com"
    assert payload.firstName is None
    assert payload.lastName is None
    assert payload.avatar is None
    assert payload.likes == []
    assert payload.bookmarks == []

