export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import {
  retrieveChapterLikesWithUserDetails,
  retrieveChapterLikesCount,
} from "@/lib/services/like";

/**
 * GET /api/v2/like/get/{chapterId} — PUBLIC (no auth), kept per endpoints.md.
 * Query: `skip=0,limit=20`. Returns all likes on the chapter with the liking
 * user's details as `PaginatedListOut[LikeWithUserOut]` (flat items).
 * Port of `get_chapter_likes_v2`.
 */
export const GET = withRoute(async (req, ctx) => {
  const { chapterId } = await ctx.params;
  const { skip, limit } = parseSkipLimit(req);

  const [items, total] = await Promise.all([
    retrieveChapterLikesWithUserDetails(chapterId, skip, limit),
    retrieveChapterLikesCount(chapterId),
  ]);
  return paginate(items, skip, limit, total);
});
