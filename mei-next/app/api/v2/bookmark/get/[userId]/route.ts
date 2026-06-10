export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAnyToken } from "@/lib/http/guards";
import {
  resolveActorUserId,
  parseTargetType,
  retrieveUserBookmark,
  retrieveUserBookmarkCount,
} from "@/lib/services/bookmark";

/**
 * GET /api/v2/bookmark/get/{userId} — member OR admin.
 * Legacy wrapper: returns ONLY the caller's data and 403s when the path `userId`
 * is not the caller's. Query: `targetType?`, `skip=0,limit=20`. Returns
 * `PaginatedListOut[BookMarkOutAsync]`. Port of `get_bookmarks_legacy_v2`.
 */
export const GET = withRoute(async (req, ctx) => {
  const claims = await verifyAnyToken(req);
  const { userId } = await ctx.params;
  const { skip, limit } = parseSkipLimit(req);
  const targetType = parseTargetType(new URL(req.url).searchParams.get("targetType"));

  const callerId = await resolveActorUserId(claims);
  if (callerId !== userId) {
    throw new HttpError(403, "Not authorized to view another user's bookmarks");
  }

  const [items, total] = await Promise.all([
    retrieveUserBookmark(callerId, targetType, skip, limit),
    retrieveUserBookmarkCount(callerId, targetType),
  ]);
  return paginate(items, skip, limit, total);
});
