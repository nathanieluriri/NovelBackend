from schemas.author_room import AuthorRoomOut


def test_author_room_out_accepts_reaction_summary_map():
    payload = {
        "_id": "a" * 24,
        "text": "author update",
        "chapterId": "b" * 24,
        "dateCreated": "2026-03-01T10:00:00+00:00",
        "lastUpdated": "2026-03-01T11:00:00+00:00",
        "reactionSummary": {"❤️": 4, "😂": 2},
    }

    room = AuthorRoomOut.model_validate(payload)

    assert room.reactionSummary == {"❤️": 4, "😂": 2}


def test_author_room_out_defaults_reaction_summary_to_empty_map():
    payload = {
        "_id": "c" * 24,
        "text": "author update",
        "chapterId": "d" * 24,
        "dateCreated": "2026-03-01T10:00:00+00:00",
        "lastUpdated": "2026-03-01T11:00:00+00:00",
    }

    room = AuthorRoomOut.model_validate(payload)

    assert room.reactionSummary == {}
