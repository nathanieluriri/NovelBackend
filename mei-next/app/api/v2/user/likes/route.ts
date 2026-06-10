export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { paginate, parseSkipLimit } from "@/lib/http/envelope";
import { HttpError } from "@/lib/http/errors";
import { verifyToken } from "@/lib/http/guards";
import { getUserDetailsWithAccessToken, retrieveUserLikes, retrieveUserLikesCount } from "@/lib/services/user";

/**
 * GET /api/v2/user/likes  (member) — PaginatedListOut[LikeOut] (flat items).
 * Port of `get_user_likes_v2` (api/v2/user.py): skip>=0 (400), limit clamped,
 * then the user's likes paginated. Legacy `build_list_payload` emits FLAT items
 * + summary (build_indexed_items returns list(items) — indexing is disabled),
 * matching the sibling /like/get endpoint over the same data.
 */
export const GET = withRoute(async (req) => {
  const { skip, limit } = parseSkipLimit(req);
  const claims = await verifyToken(req);
  const user = await getUserDetailsWithAccessToken(claims.accessToken);
  if (!user) throw new HttpError(401, "Invalid token");
  if (!user.userId) throw new HttpError(401, "Invalid token");

  const total = await retrieveUserLikesCount(user.userId);
  const likes = await retrieveUserLikes(user.userId, skip, limit);
  return paginate(likes, skip, limit, total);
});
