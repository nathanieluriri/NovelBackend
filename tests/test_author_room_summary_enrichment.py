import asyncio

from services import author_room_service
from schemas.author_room import AuthorRoomOut
from schemas.cache_summary_schema import ChapterSummaryOut
from schemas.reaction import ReactionOut


ROOM_ID = "a" * 24
CHAPTER_ID = "b" * 24
USER_ID = "1" * 24


def _author_room_payload(room_id: str = ROOM_ID, chapter_id: str = CHAPTER_ID) -> dict:
    return {
        "_id": room_id,
        "text": "author update",
        "chapterId": chapter_id,
        "dateCreated": "2026-02-01T10:00:00+00:00",
        "lastUpdated": "2026-02-01T11:00:00+00:00",
    }


def test_retrieve_author_room_by_id_attaches_chapter_summary(monkeypatch):
    async def fake_get_author_room(*args, **kwargs):
        return AuthorRoomOut.model_validate(_author_room_payload())

    async def fake_get_chapter_summary(*args, **kwargs):
        return ChapterSummaryOut(id=CHAPTER_ID, chapterLabel="Chapter 1", number=1)

    async def fake_get_reaction_summary_by_author_room_id(*args, **kwargs):
        return {"❤️": 2, "😂": 1}

    async def fake_get_reaction_by_user_and_room(*args, **kwargs):
        return ReactionOut.model_validate(
            {
                "_id": "9" * 24,
                "reaction": "❤️",
                "authorRoomId": ROOM_ID,
                "dateCreated": "2026-02-01T10:05:00+00:00",
                "lastUpdated": "2026-02-01T10:05:00+00:00",
            }
        )

    monkeypatch.setattr(author_room_service, "get_author_room", fake_get_author_room)
    monkeypatch.setattr(author_room_service, "get_chapter_summary", fake_get_chapter_summary)
    monkeypatch.setattr(
        author_room_service,
        "get_reaction_summary_by_author_room_id",
        fake_get_reaction_summary_by_author_room_id,
    )
    monkeypatch.setattr(
        author_room_service,
        "get_reaction_by_user_and_room",
        fake_get_reaction_by_user_and_room,
    )

    room = asyncio.run(
        author_room_service.retrieve_author_room_by_author_room_id(ROOM_ID, user_id=USER_ID)
    )

    assert room.chapterSummary is not None
    assert room.chapterSummary.id == CHAPTER_ID
    assert room.chapterSummary.chapterLabel == "Chapter 1"
    assert room.reactionSummary == {"❤️": 2, "😂": 1}
    assert room.userReaction == "❤️"


def test_retrieve_author_rooms_attaches_chapter_summary_for_each_item(monkeypatch):
    async def fake_get_author_rooms(*args, **kwargs):
        return [
            AuthorRoomOut.model_validate(_author_room_payload(room_id="c" * 24, chapter_id="d" * 24)),
            AuthorRoomOut.model_validate(_author_room_payload(room_id="e" * 24, chapter_id="f" * 24)),
        ]

    async def fake_get_chapter_summary(chapter_id: str):
        return ChapterSummaryOut(id=chapter_id, chapterLabel="Attached", number=2)

    async def fake_get_reaction_summaries_for_author_room_ids(author_room_ids: list[str]):
        return {
            "c" * 24: {"🔥": 3},
            # intentionally omit second room to verify default fallback
        }

    async def fake_get_reactions_by_user_for_author_room_ids(*args, **kwargs):
        return {
            "c" * 24: ReactionOut.model_validate(
                {
                    "_id": "8" * 24,
                    "reaction": "🔥",
                    "authorRoomId": "c" * 24,
                    "dateCreated": "2026-02-01T10:05:00+00:00",
                    "lastUpdated": "2026-02-01T10:05:00+00:00",
                }
            )
        }

    monkeypatch.setattr(author_room_service, "get_author_rooms", fake_get_author_rooms)
    monkeypatch.setattr(author_room_service, "get_chapter_summary", fake_get_chapter_summary)
    monkeypatch.setattr(
        author_room_service,
        "get_reaction_summaries_for_author_room_ids",
        fake_get_reaction_summaries_for_author_room_ids,
    )
    monkeypatch.setattr(
        author_room_service,
        "get_reactions_by_user_for_author_room_ids",
        fake_get_reactions_by_user_for_author_room_ids,
    )

    rooms = asyncio.run(author_room_service.retrieve_author_rooms(start=0, stop=10, user_id=USER_ID))

    assert len(rooms) == 2
    assert rooms[0].chapterSummary is not None
    assert rooms[1].chapterSummary is not None
    assert rooms[0].chapterSummary.id == "d" * 24
    assert rooms[1].chapterSummary.id == "f" * 24
    assert rooms[0].reactionSummary == {"🔥": 3}
    assert rooms[1].reactionSummary == {}
    assert rooms[0].userReaction == "🔥"
    assert rooms[1].userReaction is None
