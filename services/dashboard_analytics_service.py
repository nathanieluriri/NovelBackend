
from datetime import datetime, timedelta
from core.database import db
from schemas.admin_schema import AdminDashboardAnalytics, ReaderAnalytics,RecentChapterOut,RevenueAnalytics,PageAnalytics,ChapterAnalytics,ChangeType
from schemas.user_schema import UserOut

from typing import List


async def get_newest_users(limit: int = 8) -> List[UserOut]:
    cursor = db.users.find(
        {}
    ).sort("dateCreated", -1).limit(limit)

    results = await cursor.to_list(length=limit)
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
                "as": "pages"
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
                }
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
                "wordCount": 1
            }
        }
    ]

    results = await db.chapters.aggregate(pipeline).to_list(length=8)
    return [RecentChapterOut(**doc) for doc in results]



async def perform_analytics()->AdminDashboardAnalytics: 
    # Utility to get start and end of a day
    def day_range(date: datetime):
        return (
            datetime.combine(date, datetime.min.time()),
            datetime.combine(date, datetime.max.time())
        )

    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    start_today, end_today = day_range(today)
    start_yesterday, end_yesterday = day_range(yesterday)

    # CHAPTER ANALYTICS
    total_chapters = await db.chapters.count_documents({})
    today_chapters = await db.chapters.count_documents({"dateCreated": {"$gte": start_today, "$lte": end_today}})
    yesterday_chapters = await db.chapters.count_documents({"dateCreated": {"$gte": start_yesterday, "$lte": end_yesterday}})

    chapter_change = today_chapters - yesterday_chapters
    chapter_change_type = (
        ChangeType.increase if chapter_change > 0 else
        ChangeType.decrease if chapter_change < 0 else
        ChangeType.no_change
    )

    chapter_analytics = ChapterAnalytics(
        totalChapters=str(total_chapters),
        chapterChange=str(abs(chapter_change)),
        changeType=chapter_change_type
    )

    # PAGE ANALYTICS
    total_pages = await db.pages.count_documents({})
    today_pages = await db.pages.count_documents({"dateCreated": {"$gte": start_today, "$lte": end_today}})
    yesterday_pages = await db.pages.count_documents({"dateCreated": {"$gte": start_yesterday, "$lte": end_yesterday}})

    page_change = today_pages - yesterday_pages
    page_change_type = (
        ChangeType.increase if page_change > 0 else
        ChangeType.decrease if page_change < 0 else
        ChangeType.no_change
    )

    page_analytics = PageAnalytics(
        totalpages=str(total_pages),
        pageChange=str(abs(page_change)),
        changeType=page_change_type
    )

    # READER ANALYTICS
    total_readers = await db.users.count_documents({})
    today_readers = await db.users.count_documents({"dateCreated": {"$gte": start_today, "$lte": end_today}})
    yesterday_readers = await db.users.count_documents({"dateCreated": {"$gte": start_yesterday, "$lte": end_yesterday}})

    reader_change = today_readers - yesterday_readers
    reader_change_type = (
        ChangeType.increase if reader_change > 0 else
        ChangeType.decrease if reader_change < 0 else
        ChangeType.no_change
    )

    reader_analytics = ReaderAnalytics(
        totalReaders=str(total_readers),
        readerChange=str(abs(reader_change)),
        changeType=reader_change_type
    )
    recent_chapters =await get_recent_chapters_with_wordcount()
    recent_users = await get_newest_users()
    data = {"pageAnalytics":page_analytics,"readerAnalytics":reader_analytics,"chapterAnalytics":chapter_analytics,"revenueAnalytics":RevenueAnalytics(totalRevenue="400000",revenueChange="3",changeType=ChangeType.increase),"recentChapters":recent_chapters,"recentUsers":recent_users}
    result = AdminDashboardAnalytics(**data)
    return result
