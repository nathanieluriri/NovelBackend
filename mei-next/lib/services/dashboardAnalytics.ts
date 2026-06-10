/**
 * Dashboard analytics — port of `services/dashboard_analytics_service.py`
 * (`perform_analytics`). Drives `GET /api/v2/admin/dashboardAnalytics`.
 *
 * Behaviour reproduced 1:1:
 *  - today-vs-yesterday (UTC) count deltas for chapters / pages / users using
 *    each collection's `dateCreated` field; `changeType` is increase / decrease
 *    / "no change" from the signed delta, while the *change* number is the
 *    ABSOLUTE delta as a string (legacy `str(abs(change))`).
 *  - REVENUE is HARDCODED: totalRevenue "400000", revenueChange "3",
 *    changeType "increase" (deliberate legacy parity quirk — keep as-is).
 *  - recentChapters: chapters sorted by `dateUpdated` desc, limit 8, with a
 *    `$lookup` into `pages` matching `chapterId` as the chapter's `_id` STRING
 *    OR ObjectId; `pageCount` = count of matched pages, `wordCount` = sum of
 *    their `textCount` (`$ifNull 0`). (Legacy pipeline replicated exactly.)
 *  - recentUsers: 8 newest users by `dateCreated` desc.
 *
 * NOTE on the date range: legacy builds Python `datetime` day-bounds and passes
 * them straight to Mongo `count_documents`. The stored `dateCreated` is an ISO
 * STRING, so we build the bounds as ISO `+00:00` strings (same instants) and
 * compare lexicographically — the faithful, working form of the legacy intent.
 */
import type { Model, PipelineStage } from "mongoose";
import { db } from "@/lib/db";
import { Chapter, Page, User } from "@/lib/models";
import { toChapterOut, type RecentChapterOut } from "@/lib/serializers/chapter";
import { toUserOut, type UserOut } from "@/lib/serializers/user";
import type {
  AdminDashboardAnalytics,
  ChangeType,
  ChapterAnalytics,
  PageAnalytics,
  ReaderAnalytics,
  RevenueAnalytics,
} from "@/lib/serializers/admin";
import { toIsoOffset } from "@/lib/util/dates";

/** Signed delta → ChangeType (legacy `_change_type`). */
function changeTypeOf(delta: number): ChangeType {
  if (delta > 0) return "increase";
  if (delta < 0) return "decrease";
  return "no change";
}

/** ISO `+00:00` boundaries for a given UTC calendar day (start/end inclusive). */
function dayRange(year: number, monthIdx: number, day: number): { start: string; end: string } {
  const start = new Date(Date.UTC(year, monthIdx, day, 0, 0, 0, 0));
  // Legacy uses datetime.max.time() → 23:59:59.999999 (microseconds); ms is the
  // finest JS resolution and is more than sufficient for the inclusive bound.
  const end = new Date(Date.UTC(year, monthIdx, day, 23, 59, 59, 999));
  return {
    start: toIsoOffset(start) as string,
    end: toIsoOffset(end) as string,
  };
}

/** Count docs whose ISO-string `dateCreated` falls within an inclusive range. */
async function countInRange(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  m: Model<any>,
  range: { start: string; end: string },
): Promise<number> {
  return m.countDocuments({ dateCreated: { $gte: range.start, $lte: range.end } }).exec();
}

/**
 * recentChapters aggregation — verbatim port of
 * `get_recent_chapters_with_wordcount`'s pipeline.
 */
async function getRecentChaptersWithWordCount(): Promise<RecentChapterOut[]> {
  const pipeline: PipelineStage[] = [
    { $sort: { dateUpdated: -1 } },
    { $limit: 8 },
    {
      $lookup: {
        from: "pages",
        let: {
          chapterIdStr: { $toString: "$_id" },
          chapterIdObj: "$_id",
        },
        pipeline: [
          {
            $match: {
              $expr: {
                $or: [
                  { $eq: ["$chapterId", "$$chapterIdStr"] },
                  { $eq: ["$chapterId", "$$chapterIdObj"] },
                ],
              },
            },
          },
          {
            $project: {
              _id: 1,
              textCount: { $ifNull: ["$textCount", 0] },
            },
          },
        ],
        as: "pages",
      },
    },
    {
      $addFields: {
        pageCount: { $size: "$pages" },
        wordCount: {
          $sum: {
            $map: {
              input: "$pages",
              as: "page",
              in: { $ifNull: ["$$page.textCount", 0] },
            },
          },
        },
      },
    },
    {
      $project: {
        _id: 1,
        bookId: 1,
        number: 1,
        chapterLabel: 1,
        status: 1,
        coverImage: 1,
        dateUpdated: 1,
        pageCount: 1,
        wordCount: 1,
      },
    },
  ];

  const docs = await Chapter.aggregate(pipeline).exec();

  return (docs as Record<string, unknown>[]).map((doc) => {
    const pageCount = Number(doc.pageCount ?? 0);
    const wordCount = Number(doc.wordCount ?? 0);
    return {
      ...toChapterOut(doc, { pageCount }),
      wordCount: Number.isNaN(wordCount) ? 0 : wordCount,
    };
  });
}

/** 8 newest users by `dateCreated` desc (legacy `get_newest_users`). */
async function getNewestUsers(limit = 8): Promise<UserOut[]> {
  const docs = await User.find().sort({ dateCreated: -1 }).limit(limit).lean<Record<string, unknown>[]>();
  return docs.map((doc) => toUserOut(doc));
}

/** Port of `perform_analytics` — assembles the full AdminDashboardAnalytics. */
export async function performAnalytics(): Promise<AdminDashboardAnalytics> {
  await db();

  const now = new Date();
  const y = now.getUTCFullYear();
  const m = now.getUTCMonth();
  const d = now.getUTCDate();

  const todayRange = dayRange(y, m, d);
  // Yesterday: subtract a day via a UTC Date so month/year rollover is handled.
  const yesterdayDate = new Date(Date.UTC(y, m, d - 1));
  const yesterdayRange = dayRange(
    yesterdayDate.getUTCFullYear(),
    yesterdayDate.getUTCMonth(),
    yesterdayDate.getUTCDate(),
  );

  // CHAPTER ANALYTICS
  const totalChapters = await Chapter.countDocuments().exec();
  const todayChapters = await countInRange(Chapter, todayRange);
  const yesterdayChapters = await countInRange(Chapter, yesterdayRange);
  const chapterChange = todayChapters - yesterdayChapters;
  const chapterAnalytics: ChapterAnalytics = {
    totalChapters: String(totalChapters),
    chapterChange: String(Math.abs(chapterChange)),
    changeType: changeTypeOf(chapterChange),
  };

  // PAGE ANALYTICS
  const totalPages = await Page.countDocuments().exec();
  const todayPages = await countInRange(Page, todayRange);
  const yesterdayPages = await countInRange(Page, yesterdayRange);
  const pageChange = todayPages - yesterdayPages;
  const pageAnalytics: PageAnalytics = {
    totalpages: String(totalPages),
    pageChange: String(Math.abs(pageChange)),
    changeType: changeTypeOf(pageChange),
  };

  // READER ANALYTICS
  const totalReaders = await User.countDocuments().exec();
  const todayReaders = await countInRange(User, todayRange);
  const yesterdayReaders = await countInRange(User, yesterdayRange);
  const readerChange = todayReaders - yesterdayReaders;
  const readerAnalytics: ReaderAnalytics = {
    totalReaders: String(totalReaders),
    readerChange: String(Math.abs(readerChange)),
    changeType: changeTypeOf(readerChange),
  };

  // REVENUE ANALYTICS — HARDCODED legacy parity quirk (keep exactly).
  const revenueAnalytics: RevenueAnalytics = {
    totalRevenue: "400000",
    revenueChange: "3",
    changeType: "increase",
  };

  const recentChapters = await getRecentChaptersWithWordCount();
  const recentUsers = await getNewestUsers();

  return {
    chapterAnalytics,
    pageAnalytics,
    readerAnalytics,
    revenueAnalytics,
    recentChapters,
    recentUsers,
  };
}
