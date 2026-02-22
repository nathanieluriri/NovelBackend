from schemas.likes_schema import LikeOut


def test_like_out_accepts_iso_string_date_created():
    payload = {
        "_id": "a" * 24,
        "userId": "b" * 24,
        "role": "member",
        "chapterId": "c" * 24,
        "chapaterLabel": "Chapter 1",
        "dateCreated": "2025-11-09T17:35:32.964715+00:00",
    }

    like = LikeOut(**payload)

    assert like.dateCreated == "2025-11-09T17:35:32.964715+00:00"


def test_like_out_converts_integer_date_created_to_iso_string():
    payload = {
        "_id": "d" * 24,
        "userId": "e" * 24,
        "role": "member",
        "chapterId": "f" * 24,
        "chapaterLabel": "Chapter 2",
        "dateCreated": 1731182400,
    }

    like = LikeOut(**payload)

    assert isinstance(like.dateCreated, str)
    assert like.dateCreated.endswith("+00:00")
