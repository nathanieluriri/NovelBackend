export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { HttpError } from "@/lib/http/errors";
import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { getOneUserDetails } from "@/lib/services/userAdmin";

/**
 * GET /api/v2/user/{userId}/user-details — admin: one user with chapter details.
 * Port of `get_particular_user_data` (../api/v1/user.py) → `get_one_user_details`.
 *
 * Returns `UserOutChapterDetails`: the user plus, for every unlocked chapter,
 * the full chapter joined with a `hasRead` flag from the `read` collection.
 * Missing user → 404 "User details not found".
 */
export const GET = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { userId } = await ctx.params;
  const result = await getOneUserDetails(userId);
  if (!result) throw new HttpError(404, "User details not found");
  return result;
});
