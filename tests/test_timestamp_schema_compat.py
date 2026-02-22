from schemas.author_room import AuthorRoomOut
from schemas.reaction import ReactionOut


def test_reaction_out_accepts_integer_timestamps():
    payload = {
        "_id": "a" * 24,
        "reaction": "like",
        "authorRoomId": "b" * 24,
        "dateCreated": 1731182400,
        "lastUpdated": 1731182401,
    }

    reaction = ReactionOut.model_validate(payload)

    assert reaction.id == "a" * 24
    assert isinstance(reaction.date_created, str)
    assert reaction.date_created.endswith("+00:00")
    assert isinstance(reaction.last_updated, str)
    assert reaction.last_updated.endswith("+00:00")


def test_author_room_out_accepts_integer_timestamps():
    payload = {
        "_id": "c" * 24,
        "text": "author note",
        "chapterId": "d" * 24,
        "dateCreated": 1731182400,
        "lastUpdated": 1731182401,
    }

    author_room = AuthorRoomOut.model_validate(payload)

    assert author_room.id == "c" * 24
    assert isinstance(author_room.date_created, str)
    assert author_room.date_created.endswith("+00:00")
    assert isinstance(author_room.last_updated, str)
    assert author_room.last_updated.endswith("+00:00")

