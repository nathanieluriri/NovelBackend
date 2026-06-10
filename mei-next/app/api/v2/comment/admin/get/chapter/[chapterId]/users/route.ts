export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAdminToken } from "@/lib/http/guards";
import {
  retrieveChapterCommentUsers,
  retrieveChapterCommentUsersCount,
} from "@/lib/services/comment";

/**
 * GET /api/v2/comment/admin/get/chapter/{chapterId}/users — admin only.
 * Query: `skip=0,limit=20`. Returns per-user comment-interaction rollups as
 * `PaginatedListOut[ChapterInteractionUserOut]` (flat items). The chapter must
 * exist (404 "Chapter not found"). Port of `get_chapter_comment_users_v2`.
 */
export const GET = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { chapterId } = await ctx.params;
  const { skip, limit } = parseSkipLimit(req);

  const [items, total] = await Promise.all([
    retrieveChapterCommentUsers(chapterId, skip, limit),
    retrieveChapterCommentUsersCount(chapterId),
  ]);
  return paginate(items, skip, limit, total);
});
