import asyncio

import pytest
from fastapi import HTTPException

from services import reaction_service
from schemas.author_room import AuthorRoomOut
from schemas.reaction import ReactionCreate, ReactionOut, ReactionUpdate


USER_ID = "1" * 24
ROOM_ID = "2" * 24
CHAPTER_ID = "3" * 24


def _reaction_out_payload(room_id: str = ROOM_ID, reaction: str = "❤️") -> dict:
    return {
        "_id": "4" * 24,
        "reaction": reaction,
        "authorRoomId": room_id,
        "dateCreated": "2026-03-01T10:00:00+00:00",
        "lastUpdated": "2026-03-01T11:00:00+00:00",
    }


def _author_room_out(room_id: str = ROOM_ID, chapter_id: str = CHAPTER_ID) -> AuthorRoomOut:
    return AuthorRoomOut.model_validate(
        {
            "_id": room_id,
            "text": "author update",
            "chapterId": chapter_id,
            "dateCreated": "2026-03-01T10:00:00+00:00",
            "lastUpdated": "2026-03-01T11:00:00+00:00",
        }
    )


def _chapter_payload(chapter_id: str = CHAPTER_ID) -> dict:
    return {
        "_id": chapter_id,
        "bookId": "5" * 24,
        "chapterLabel": "Chapter 1",
        "number": 1,
        "accessType": "paid",
        "unlockBundleId": "bundle-1",
    }


def _user_payload(user_id: str = USER_ID) -> dict:
    return {
        "_id": user_id,
        "email": "reader@example.com",
        "unlockedChapters": [],
        "subscription": {"active": False, "expiresAt": None},
    }


def test_ensure_reaction_access_rejects_inaccessible_member(monkeypatch):
    async def fake_get_author_room(*args, **kwargs):
        return _author_room_out()

    async def fake_get_chapter_by_chapter_id(*args, **kwargs):
        return _chapter_payload()

    async def fake_get_user_by_user_id(*args, **kwargs):
        return _user_payload()

    async def fake_model_async_validate(self):
        return self

    async def fake_has_chapter_access(*args, **kwargs):
        return False

    monkeypatch.setattr(reaction_service, "get_author_room", fake_get_author_room)
    monkeypatch.setattr(reaction_service, "get_chapter_by_chapter_id", fake_get_chapter_by_chapter_id)
    monkeypatch.setattr(reaction_service, "get_user_by_userId", fake_get_user_by_user_id)
    monkeypatch.setattr(reaction_service.ChapterOut, "model_async_validate", fake_model_async_validate)
    monkeypatch.setattr(reaction_service, "has_chapter_access", fake_has_chapter_access)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(reaction_service._ensure_reaction_access(user_id=USER_ID, author_room_id=ROOM_ID))

    assert exc.value.status_code == 403
    assert exc.value.detail == "You do not have access to react to this chapter"


def test_add_reaction_raises_conflict_when_user_already_reacted(monkeypatch):
    async def fake_ensure_reaction_access(*args, **kwargs):
        return None

    async def fake_get_reaction_by_user_and_room(*args, **kwargs):
        return ReactionOut.model_validate(_reaction_out_payload())

    monkeypatch.setattr(reaction_service, "_ensure_reaction_access", fake_ensure_reaction_access)
    monkeypatch.setattr(reaction_service, "get_reaction_by_user_and_room", fake_get_reaction_by_user_and_room)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            reaction_service.add_reaction(
                ReactionCreate(reaction="❤️", authorRoomId=ROOM_ID, userId=USER_ID)
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "You have already reacted to this author room"


def test_add_reaction_creates_when_member_has_access(monkeypatch):
    async def fake_ensure_reaction_access(*args, **kwargs):
        return None

    async def fake_get_reaction_by_user_and_room(*args, **kwargs):
        return None

    async def fake_create_reaction(reaction_data):
        return ReactionOut.model_validate(
            {
                "_id": "6" * 24,
                "reaction": reaction_data.reaction,
                "authorRoomId": reaction_data.authorRoomId,
                "dateCreated": "2026-03-01T10:00:00+00:00",
                "lastUpdated": "2026-03-01T11:00:00+00:00",
            }
        )

    monkeypatch.setattr(reaction_service, "_ensure_reaction_access", fake_ensure_reaction_access)
    monkeypatch.setattr(reaction_service, "get_reaction_by_user_and_room", fake_get_reaction_by_user_and_room)
    monkeypatch.setattr(reaction_service, "create_reaction", fake_create_reaction)

    created = asyncio.run(
        reaction_service.add_reaction(
            ReactionCreate(reaction="🔥", authorRoomId=ROOM_ID, userId=USER_ID)
        )
    )

    assert created.authorRoomId == ROOM_ID
    assert created.reaction == "🔥"


def test_update_reaction_requires_reaction_value():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            reaction_service.update_reaction_by_id(
                user_id=USER_ID,
                author_room_id=ROOM_ID,
                reaction_data=ReactionUpdate(),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "reaction is required"
