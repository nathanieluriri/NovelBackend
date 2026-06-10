export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { verifyAdminToken } from "@/lib/http/guards";
import { removeComment } from "@/lib/services/comment";

/**
 * DELETE /api/v2/comment/admin/remove/{commentId} — admin only.
 * Deletes any comment by id (NOT scoped to a user). 404 "Resource already
 * deleted" when nothing was removed (invalid id or already gone). Returns the
 * removed `CommentOut`. Port of `admin_remove_comment`.
 */
export const DELETE = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { commentId } = await ctx.params;

  const removed = await removeComment(commentId);
  if (removed === null) throw new HttpError(404, "Resource already deleted");
  return removed;
});
