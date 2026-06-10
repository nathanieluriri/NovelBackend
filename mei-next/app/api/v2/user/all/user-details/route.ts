export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { HttpError } from "@/lib/http/errors";
import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { getAllUserDetails } from "@/lib/services/userAdmin";

/**
 * GET /api/v2/user/all/user-details — admin: list every user as `UserOut`.
 * Port of `get_user_data` (../api/v1/user.py) → `get_all_user_details`.
 *
 * Legacy quirks reproduced:
 *  - admin-only (`verify_admin_token`).
 *  - returns the BARE list (not PaginatedListOut — withRoute envelopes it as
 *    `data: [...]`); `get_all_users` is unpaginated.
 *  - an EMPTY result is falsy in the legacy `if result:` guard → 404
 *    "No user details found".
 */
export const GET = withRoute(async (req) => {
  await verifyAdminToken(req);
  const users = await getAllUserDetails();
  if (users.length === 0) throw new HttpError(404, "No user details found");
  return users;
});
