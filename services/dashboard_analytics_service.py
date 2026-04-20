from datetime import datetime, timedelta
from typing import List

from core.database import client
from schemas.admin_schema import (
    AdminDashboardAnalytics,
    ChangeType,
    ChapterAnalytics,
    PageAnalytics,
    ReaderAnalytics,
    RecentChapterOut,
    RevenueAnalytics,
)
from schemas.user_schema import UserOut


USERS = "users"
CHAPTERS = "chapters"
PAGES = "pages"


async def get_newest_users(limit: int = 8) -> List[UserOut]:
    results = await client.find_many(
        USERS,
        sort=[("dateCreated", -1)],
        limit=limit,
    )
    return [UserOut(**doc) for doc in results]


async def get_recent_chapters_with_wordcount() -> List[RecentChapterOut]:
    pipeline = [
        {"$sort": {"dateUpdated": -1}},
        {"$limit": 8},
        {
            "$lookup": {
                "from": "pages",
                "let": {
                    "chapterIdStr": {"$toString": "$_id"},
                    "chapterIdObj": "$_id",
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$or": [
                                    {"$eq": ["$chapterId", "$$chapterIdStr"]},
                                    {"$eq": ["$chapterId", "$$chapterIdObj"]},
                                ]
                            }
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "textCount": {"$ifNull": ["$textCount", 0]},
                        }
                    },
                ],
                "as": "pages",
            }
        },
        {
            "$addFields": {
                "pageCount": {"$size": "$pages"},
                "wordCount": {
                    "$sum": {
                        "$map": {
                            "input": "$pages",
                            "as": "page",
                            "in": {"$ifNull": ["$$page.textCount", 0]},
                        }
                    }
                },
            }
        },
        {
            "$project": {
                "_id": 1,
                "bookId": 1,
                "number": 1,
                "chapterLabel": 1,
                "status": 1,
                "coverImage": 1,
                "dateUpdated": 1,
                "pageCount": 1,
                "wordCount": 1,
            }
        },
    ]
    results = await client.aggregate(CHAPTERS, pipeline, length=8)
    return [RecentChapterOut(**doc) for doc in results]


def _change_type(delta: int) -> ChangeType:
    if delta > 0:
        return ChangeType.increase
    if delta < 0:
        return ChangeType.decrease
    return ChangeType.no_change


async def perform_analytics() -> AdminDashboardAnalytics:
    def day_range(date: datetime):
        return (
            datetime.combine(date, datetime.min.time()),
            datetime.combine(date, datetime.max.time()),
        )

    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    start_today, end_today = day_range(today)
    start_yesterday, end_yesterday = day_range(yesterday)

    today_range = {"$gte": start_today, "$lte": end_today}
    yesterday_range = {"$gte": start_yesterday, "$lte": end_yesterday}

    # CHAPTER ANALYTICS
    total_chapters = await client.count(CHAPTERS)
    today_chapters = await client.count(CHAPTERS, {"dateCreated": today_range})
    yesterday_chapters = await client.count(
        CHAPTERS, {"dateCreated": yesterday_range}
    )
    chapter_change = today_chapters - yesterday_chapters
    chapter_analytics = ChapterAnalytics(
        totalChapters=str(total_chapters),
        chapterChange=str(abs(chapter_change)),
        changeType=_change_type(chapter_change),
    )

    # PAGE ANALYTICS
    total_pages = await client.count(PAGES)
    today_pages = await client.count(PAGES, {"dateCreated": today_range})
    yesterday_pages = await client.count(PAGES, {"dateCreated": yesterday_range})
    page_change = today_pages - yesterday_pages
    page_analytics = PageAnalytics(
        totalpages=str(total_pages),
        pageChange=str(abs(page_change)),
        changeType=_change_type(page_change),
    )

    # READER ANALYTICS
    total_readers = await client.count(USERS)
    today_readers = await client.count(USERS, {"dateCreated": today_range})
    yesterday_readers = await client.count(
        USERS, {"dateCreated": yesterday_range}
    )
    reader_change = today_readers - yesterday_readers
    reader_analytics = ReaderAnalytics(
        totalReaders=str(total_readers),
        readerChange=str(abs(reader_change)),
        changeType=_change_type(reader_change),
    )

    recent_chapters = await get_recent_chapters_with_wordcount()
    recent_users = await get_newest_users()
    return AdminDashboardAnalytics(
        pageAnalytics=page_analytics,
        readerAnalytics=reader_analytics,
        chapterAnalytics=chapter_analytics,
        revenueAnalytics=RevenueAnalytics(
            totalRevenue="400000",
            revenueChange="3",
            changeType=ChangeType.increase,
        ),
        recentChapters=recent_chapters,
        recentUsers=recent_users,
    )
