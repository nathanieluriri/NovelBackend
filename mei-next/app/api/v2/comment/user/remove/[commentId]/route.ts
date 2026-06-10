export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { verifyAnyToken } from "@/lib/http/guards";
import {
  resolveActorUserId,
  removeCommentByUserIdAndCommentId,
} from "@/lib/services/comment";

/**
 * DELETE /api/v2/comment/user/remove/{commentId} — member OR admin.
 * Deletes the caller's own comment (scoped to `{_id, userId}`). 404 "Resource
 * already deleted" when nothing was removed (invalid id, already gone, or another
 * user's comment). Returns the removed `CommentOut`. Port of
 * `user_remove_comment`.
 */
export const DELETE = withRoute(async (req, ctx) => {
  const claims = await verifyAnyToken(req);
  const { commentId } = await ctx.params;

  const userId = await resolveActorUserId(claims);
  const removed = await removeCommentByUserIdAndCommentId(commentId, userId);
  if (removed === null) throw new HttpError(404, "Resource already deleted");
  return removed;
});
