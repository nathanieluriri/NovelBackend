export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import {
  retrieveTargetComments,
  retrieveTargetCommentsCount,
} from "@/lib/services/comment";

/**
 * GET /api/v2/comment/get/{chapterId} — PUBLIC (no auth).
 * Legacy chapter wrapper: returns the chapter's comments (targetType forced to
 * "chapter", targetId = chapterId — incl. the OR-fallback for chapter-only rows).
 * Query: `skip=0,limit=20`. Returns `PaginatedListOut[CommentOut]` (flat items).
 * Port of `get_chapter_comments_v2`.
 *
 * Next.js routing: the sibling static `target` segment wins over this dynamic
 * `[chapterId]` route automatically, so `/get/target/...` is never shadowed.
 */
export const GET = withRoute(async (req, ctx) => {
  const { chapterId } = await ctx.params;
  const { skip, limit } = parseSkipLimit(req);

  const [items, total] = await Promise.all([
    retrieveTargetComments("chapter", chapterId, skip, limit),
    retrieveTargetCommentsCount("chapter", chapterId),
  ]);
  return paginate(items, skip, limit, total);
});
