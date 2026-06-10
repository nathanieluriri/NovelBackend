export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { removeLike } from "@/lib/services/like";

/**
 * DELETE /api/v2/like/remove/{likeId} — PUBLIC (no auth), kept per endpoints.md.
 * Removal is by `likeId` only (not scoped to a user). Returns the removed
 * `LikeOut`; 404 "Resource already deleted" when nothing was deleted (an invalid
 * id also yields 404). Port of `unlike`.
 */
export const DELETE = withRoute(async (req, ctx) => {
  const { likeId } = await ctx.params;
  const removed = await removeLike(likeId);
  if (removed === null) throw new HttpError(404, "Resource already deleted");
  return removed;
});
