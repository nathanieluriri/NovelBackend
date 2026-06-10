export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAnyToken } from "@/lib/http/guards";
import {
  resolveActorUserId,
  parseTargetType,
  retrieveUserBookmark,
  retrieveUserBookmarkCount,
} from "@/lib/services/bookmark";

/**
 * GET /api/v2/bookmark/get — member OR admin.
 * Query: `targetType?`, `skip=0,limit=20`. Returns the caller's bookmarks as
 * `PaginatedListOut[BookMarkOutAsync]` (flat items). Port of `get_bookmarks_v2`.
 */
export const GET = withRoute(async (req) => {
  const claims = await verifyAnyToken(req);
  const { skip, limit } = parseSkipLimit(req);
  const targetType = parseTargetType(new URL(req.url).searchParams.get("targetType"));

  const userId = await resolveActorUserId(claims);
  const [items, total] = await Promise.all([
    retrieveUserBookmark(userId, targetType, skip, limit),
    retrieveUserBookmarkCount(userId, targetType),
  ]);
  return paginate(items, skip, limit, total);
});
