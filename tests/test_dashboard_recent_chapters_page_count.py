import asyncio

from services import dashboard_analytics_service


class _FakeAggregateCursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length=None):
        if length is None:
            return self.rows
        return self.rows[:length]


class _FakeChapterCollection:
    def __init__(self, rows):
        self.rows = rows
        self.captured_pipeline = None

    def aggregate(self, pipeline):
        self.captured_pipeline = pipeline
        return _FakeAggregateCursor(self.rows)


class _FakeCountCollection:
    def __init__(self, values):
        self.values = values
        self.index = 0

    async def count_documents(self, _query):
        value = self.values[self.index]
        self.index += 1
        return value


def test_get_recent_chapters_with_wordcount_uses_type_safe_lookup_and_sets_page_count(monkeypatch):
    rows = [
        {
            "_id": "a" * 24,
            "bookId": "b" * 24,
            "number": 1,
            "chapterLabel": "Chapter 1",
            "status": "free",
            "coverImage": None,
            "dateUpdated": "2026-02-25T10:00:00+00:00",
            "pageCount": 3,
            "wordCount": 120,
        }
    ]
    chapter_collection = _FakeChapterCollection(rows)
    fake_db = type("FakeDB", (), {"chapters": chapter_collection})()
    monkeypatch.setattr(dashboard_analytics_service, "db", fake_db)

    chapters = asyncio.run(dashboard_analytics_service.get_recent_chapters_with_wordcount())

    assert len(chapters) == 1
    assert chapters[0].pageCount == 3
    assert chapters[0].wordCount == 120

    pipeline = chapter_collection.captured_pipeline
    lookup_stage = next(stage for stage in pipeline if "$lookup" in stage)
    add_fields_stage = next(stage for stage in pipeline if "$addFields" in stage)

    lookup = lookup_stage["$lookup"]
    assert lookup["let"]["chapterIdStr"] == {"$toString": "$_id"}
    assert {"$eq": ["$chapterId", "$$chapterIdStr"]} in lookup["pipeline"][0]["$match"]["$expr"]["$or"]
    assert add_fields_stage["$addFields"]["pageCount"] == {"$size": "$pages"}


def test_perform_analytics_preserves_recent_chapter_page_count(monkeypatch):
    fake_db = type(
        "FakeDB",
        (),
        {
            "chapters": _FakeCountCollection([10, 2, 1]),
            "pages": _FakeCountCollection([22, 3, 1]),
            "users": _FakeCountCollection([5, 1, 1]),
        },
    )()

    async def fake_recent_chapters():
        return [
            {
                "_id": "c" * 24,
                "bookId": "d" * 24,
                "number": 2,
                "chapterLabel": "Chapter 2",
                "status": "free",
                "dateUpdated": "2026-02-25T12:00:00+00:00",
                "pageCount": 7,
                "wordCount": 300,
            }
        ]

    async def fake_recent_users():
        return []

    monkeypatch.setattr(dashboard_analytics_service, "db", fake_db)
    monkeypatch.setattr(dashboard_analytics_service, "get_recent_chapters_with_wordcount", fake_recent_chapters)
    monkeypatch.setattr(dashboard_analytics_service, "get_newest_users", fake_recent_users)

    result = asyncio.run(dashboard_analytics_service.perform_analytics())

    assert len(result.recentChapters) == 1
    assert result.recentChapters[0].pageCount == 7
