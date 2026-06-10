export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAnyToken } from "@/lib/http/guards";
import {
  resolveActorUserId,
  retrieveUserLikes,
  retrieveUserLikesCount,
} from "@/lib/services/like";

/**
 * GET /api/v2/like/get — member OR admin.
 * Query: `skip=0,limit=20`. Returns the caller's likes as
 * `PaginatedListOut[LikeOut]` (flat items). Port of `get_user_likes_v2`.
 */
export const GET = withRoute(async (req) => {
  const claims = await verifyAnyToken(req);
  const { skip, limit } = parseSkipLimit(req);

  const userId = await resolveActorUserId(claims);
  const [items, total] = await Promise.all([
    retrieveUserLikes(userId, skip, limit),
    retrieveUserLikesCount(userId),
  ]);
  return paginate(items, skip, limit, total);
});
