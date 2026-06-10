export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { verifyAnyToken } from "@/lib/http/guards";
import {
  resolveActorUserId,
  removeBookmarkForUser,
} from "@/lib/services/bookmark";

/**
 * DELETE /api/v2/bookmark/remove/{bookmarkId} — member OR admin.
 * Deletes the caller's bookmark (scoped to userId). 404 "Resource already
 * deleted" when nothing was removed (invalid id, already gone, or another user's
 * bookmark). Returns the removed `BookMarkOutAsync`. Port of `delete_a_bookmark`.
 */
export const DELETE = withRoute(async (req, ctx) => {
  const claims = await verifyAnyToken(req);
  const { bookmarkId } = await ctx.params;

  const userId = await resolveActorUserId(claims);
  const removed = await removeBookmarkForUser(bookmarkId, userId);
  if (removed === null) throw new HttpError(404, "Resource already deleted");
  return removed;
});
