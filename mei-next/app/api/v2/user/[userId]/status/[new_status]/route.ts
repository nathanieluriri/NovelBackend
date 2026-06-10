export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { HttpError } from "@/lib/http/errors";
import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { updateUserStatus } from "@/lib/services/userAdmin";
import type { UserStatus } from "@/lib/serializers";

/**
 * PATCH /api/v2/user/{userId}/status/{new_status} — admin: set a user's status.
 * Port of `update_user_data` (../api/v1/user.py) → `update_user_details`.
 *
 * `new_status` is a `UserStatus` path enum ("Active" | "Inactive" |
 * "Suspended"); the legacy FastAPI path validation rejects anything else with
 * a 422. The update `$set`s the full UserUpdate dump (firstName/lastName/avatar
 * blanked to null + the new status) and returns the updated `UserOut`.
 * Missing user → 404 "User status update failed".
 */
const VALID_STATUSES: readonly UserStatus[] = ["Active", "Inactive", "Suspended"];

export const PATCH = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { userId, new_status: newStatus } = await ctx.params;

  if (!VALID_STATUSES.includes(newStatus as UserStatus)) {
    throw new HttpError(422, "Validation failed", [
      {
        type: "enum",
        loc: ["path", "new_status"],
        msg: `Input should be 'Active', 'Inactive' or 'Suspended'`,
        input: newStatus,
      },
    ]);
  }

  const result = await updateUserStatus(userId, newStatus as UserStatus);
  if (!result) throw new HttpError(404, "User status update failed");
  return result;
});
