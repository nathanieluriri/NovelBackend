export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { HttpError } from "@/lib/http/errors";
import { withRoute } from "@/lib/http/route";
import { buildListMeta } from "@/lib/http/envelope";
import { verifyToken } from "@/lib/http/guards";
import { getUserReadingProgress } from "@/lib/services/readingProgress";
import type { ReadingProgressOut } from "@/lib/serializers";
import {
  getUserDetailsWithAccessToken,
  retrieveUserBookmarks,
  retrieveUserBookmarksCount,
  retrieveUserLikes,
  retrieveUserLikesCount,
} from "@/lib/services/user";

/**
 * GET /api/v2/user/details  (member) — UserDetailsV2Out.
 * Native v2 aggregate, port of `get_user_details_v2` (api/v2/user.py):
 *  - totals (likes/bookmarks counts),
 *  - previews limited to 100, indexed items (1-based index — legacy `i + 1`),
 *  - readingProgress (null if absent — 404/403 from the seam are swallowed),
 *  - likesMeta / bookmarksMeta (skip=0, limit=100, returned, total).
 *
 * NOTE: indexed item wrapping here is the user-v2 indexed variant (schema.md §3)
 * — the `details` aggregate uses a 1-based index per the legacy handler.
 */

/** Swallow only the 403/404 the reading-progress seam raises when absent. */
async function readingProgressOrNull(userId: string): Promise<ReadingProgressOut | null> {
  try {
    return await getUserReadingProgress(userId);
  } catch (err) {
    if (err instanceof HttpError && (err.status === 403 || err.status === 404)) return null;
    throw err;
  }
}

export const GET = withRoute(async (req) => {
  const claims = await verifyToken(req);
  const user = await getUserDetailsWithAccessToken(claims.accessToken);
  if (!user) throw new HttpError(401, "Invalid token");
  if (!user.userId) throw new HttpError(401, "Invalid token");

  const userId = user.userId;

  const [likesTotal, bookmarksTotal] = await Promise.all([
    retrieveUserLikesCount(userId),
    retrieveUserBookmarksCount(userId),
  ]);

  const [likesPreview, bookmarksPreview, readingProgress] = await Promise.all([
    retrieveUserLikes(userId, 0, 100),
    retrieveUserBookmarks(userId, 0, 100),
    readingProgressOrNull(userId),
  ]);

  const likesIndexed = likesPreview.map((item, i) => ({ index: i + 1, item }));
  const bookmarksIndexed = bookmarksPreview.map((item, i) => ({ index: i + 1, item }));

  return {
    userId,
    email: user.email,
    firstName: user.firstName,
    lastName: user.lastName,
    avatar: user.avatar,
    summary: { totalLikes: likesTotal, totalBookmarks: bookmarksTotal },
    likes: likesIndexed,
    bookmarks: bookmarksIndexed,
    readingProgress,
    likesMeta: buildListMeta(0, 100, likesIndexed.length, likesTotal),
    bookmarksMeta: buildListMeta(0, 100, bookmarksIndexed.length, bookmarksTotal),
  };
});
