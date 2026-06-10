export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAdminToken } from "@/lib/http/guards";
import {
  retrieveChapterLikeUsers,
  retrieveChapterLikeUsersCount,
} from "@/lib/services/like";

/**
 * GET /api/v2/like/admin/get/chapter/{chapterId}/users — admin only.
 * Query: `skip=0,limit=20`. Returns per-user like-interaction rollups as
 * `PaginatedListOut[ChapterInteractionUserOut]` (flat items). The chapter must
 * exist (404 "Chapter not found"). Port of `get_chapter_like_users_v2`.
 */
export const GET = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { chapterId } = await ctx.params;
  const { skip, limit } = parseSkipLimit(req);

  const [items, total] = await Promise.all([
    retrieveChapterLikeUsers(chapterId, skip, limit),
    retrieveChapterLikeUsersCount(chapterId),
  ]);
  return paginate(items, skip, limit, total);
});
