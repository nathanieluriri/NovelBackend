export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyAnyToken } from "@/lib/http/guards";
import { resolveActorUserId, updateComment } from "@/lib/services/comment";

/**
 * PATCH /api/v2/comment/update — member OR admin. Body `UpdateCommentBaseRequest`
 * `{ commentId, text }` (no extra validators per legacy comments_schema.py).
 * Updates the caller's OWN comment only (scoped to `{_id, userId}`). 404
 * "Resource already deleted" when nothing matched (invalid id, not the owner, or
 * gone). Returns the updated `CommentOut`. Port of `update_comment_route`.
 */

const updateCommentBaseRequest = z.object({
  commentId: z.string(),
  text: z.string(),
});

export const PATCH = withRoute(async (req) => {
  const claims = await verifyAnyToken(req);
  const body = await parseBody(req, updateCommentBaseRequest);

  const userId = await resolveActorUserId(claims);
  const updated = await updateComment(body.commentId, userId, body.text);
  if (updated === null) throw new HttpError(404, "Resource already deleted");
  return updated;
});
