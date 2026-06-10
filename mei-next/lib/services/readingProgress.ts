/**
 * Reading-progress seam — port of `services/reading_progress_service.py` +
 * `repositories/reading_progress_repo.py` (see ../nextjs-migration/reading-progress.md).
 *
 * Pinned seam (CONVENTIONS.md `@/lib/services/readingProgress`):
 *   trackReadingProgress(userId?, chapterId?, pageId?): Promise<void>   // guarded idempotent upsert
 *   getUserReadingProgress(userId): Promise<ReadingProgressOut>         // 404/403 per reading-progress.md
 *
 * The legacy app fired `track_user_reading_progress` from a FastAPI BackgroundTask
 * after a single-page GET; on Vercel that becomes one idempotent Mongo upsert run
 * via `after()` (scheduled in the route handler, not here).
 */
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { nowIso } from "@/lib/util/dates";
import { ReadingProgress, Chapter, Page, User } from "@/lib/models";
import { hasChapterAccess } from "@/lib/services/access";
import { getChapterSummary, getPageSummary } from "@/lib/cache/summary";
import { toReadingProgressOut, type ReadingProgressOut } from "@/lib/serializers";

const NO_PROGRESS_MESSAGE = "No stopped-reading information found";

/**
 * Guarded idempotent upsert (the drop-in replacement for the legacy background
 * task). No-op when any of the three ids is falsy — mirrors the legacy guard.
 * Concurrent calls are safe under the unique `userId` index (last writer wins).
 * Dates use the `+00:00` (`toIsoOffset`) format, NOT `Z`, for wire byte-parity.
 */
export async function trackReadingProgress(
  userId?: string,
  chapterId?: string,
  pageId?: string,
): Promise<void> {
  if (!userId || !chapterId || !pageId) return; // guard: mirror legacy no-op
  await db();
  const now = nowIso();
  await ReadingProgress.collection.updateOne(
    { userId },
    {
      $set: { userId, chapterId, pageId, dateUpdated: now },
      $setOnInsert: { dateCreated: now },
    },
    { upsert: true },
  );
}

/**
 * Read path (`GET /api/v2/user/reading/progress`). Reproduces the legacy
 * `get_user_reading_progress` exactly:
 *  1. single doc for the user → 404 if absent.
 *  2. chapter + page load → 404 if missing, or if page.chapterId !== progress.chapterId.
 *  3. access gate via hasChapterAccess (free → ok; else subscription active OR
 *     unlocked/entitled) → 403 otherwise.
 *  4. hydrate chapterSummary / pageSummary through the Redis summary cache.
 */
export async function getUserReadingProgress(userId: string): Promise<ReadingProgressOut> {
  if (!userId) throw new HttpError(401, "User identity is missing");
  await db();

  const progress = await ReadingProgress.findOne({ userId }).lean<Record<string, unknown>>();
  if (!progress) throw new HttpError(404, NO_PROGRESS_MESSAGE);

  const chapterId = String(progress.chapterId ?? "");
  const pageId = String(progress.pageId ?? "");

  const chapter = await Chapter.findById(chapterId).lean<Record<string, unknown>>();
  if (!chapter) throw new HttpError(404, NO_PROGRESS_MESSAGE);

  const page = await Page.findById(pageId).lean<Record<string, unknown>>();
  if (!page || String(page.chapterId ?? "") !== chapterId) {
    throw new HttpError(404, NO_PROGRESS_MESSAGE);
  }

  const user = await loadUser(userId);
  const canAccess = await hasChapterAccess(user, chapter);
  if (!canAccess) {
    throw new HttpError(
      403,
      "Cannot access stopped-reading info: subscription expired, " +
        "chapter is not free, and chapter is not unlocked.",
    );
  }

  const chapterSummary = await getChapterSummary(chapterId);
  const pageSummary = await getPageSummary(pageId);

  return toReadingProgressOut(progress, { chapterSummary, pageSummary });
}

/**
 * The legacy read path takes the resolved `UserOut`; here the route already has
 * the member's User doc loaded (resolveReader). To keep the seam signature
 * `userId`-only, we re-load the user document the same way the access gate
 * expects (`subscription` + `unlockedChapters` live on it).
 */
async function loadUser(userId: string): Promise<Record<string, unknown>> {
  const user = await User.findById(userId).lean<Record<string, unknown>>();
  if (!user) throw new HttpError(404, NO_PROGRESS_MESSAGE);
  return user;
}
