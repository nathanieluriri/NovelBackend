export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyAnyToken } from "@/lib/http/guards";
import { resolveActorUserId, addCommentForTarget } from "@/lib/services/comment";
import type { InteractionTargetType, CommentType } from "@/lib/serializers";

/**
 * POST /api/v2/comment/create — member OR admin. Body `CommentCreateRequest`.
 * Returns `CommentOut`. The target must exist (404 "Book/Chapter/Page not
 * found"). `role` is taken from the JWT claim, `userId` from the access-token
 * row — exactly legacy `_get_actor`. Port of `create_comment` +
 * `add_comment_for_target`.
 *
 * Validators mirror `CommentCreateRequest` (schema.md §5 / comments_schema.py):
 *  - before: legacy `chapterId`-only payload (no targetType/targetId) → targetType
 *    "chapter", targetId = chapterId.
 *  - after: targetType AND targetId required; targetId must be exactly 24 chars;
 *    parentCommentId (when present) must be exactly 24 chars; reply_comment /
 *    reply_reply REQUIRE parentCommentId; reply_target / Reply To Chapter FORBID
 *    it. All surface as Pydantic-shaped 422s.
 */

const COMMENT_TYPES = [
  "reply_target",
  "Reply To Chapter",
  "Reply To Comment",
  "Reply To Reply",
] as const;

const commentCreateRequest = z.object({
  text: z.string(),
  targetType: z.enum(["book", "chapter", "page"]).nullish(),
  targetId: z.string().nullish(),
  chapterId: z.string().nullish(),
  parentCommentId: z.string().nullish(),
  commentType: z.enum(COMMENT_TYPES).nullish(),
});

function valueError(msg: string): HttpError {
  return new HttpError(422, "Validation failed", [
    { type: "value_error", loc: ["body"], msg: `Value error, ${msg}`, input: null },
  ]);
}

export const POST = withRoute(async (req) => {
  const claims = await verifyAnyToken(req);
  const body = await parseBody(req, commentCreateRequest);

  // before-validator: legacy chapterId-only normalization.
  let targetType: InteractionTargetType | null = body.targetType ?? null;
  let targetId: string | null = body.targetId ?? null;
  const chapterId = body.chapterId ?? null;
  if (targetType === null && targetId === null && chapterId !== null) {
    targetType = "chapter";
    targetId = chapterId;
  }

  const parentCommentId = body.parentCommentId ?? null;
  // commentType defaults to reply_target (pydantic field default).
  const commentType: CommentType = (body.commentType ?? "reply_target") as CommentType;

  // after-validator (order mirrors comments_schema.py).
  if (targetType === null || targetId === null) {
    throw valueError("targetType and targetId are required");
  }
  if (targetId.length !== 24) {
    throw valueError("targetId must be exactly 24 characters long");
  }
  if (parentCommentId !== null && parentCommentId.length !== 24) {
    throw valueError("parentCommentId must be exactly 24 characters long");
  }
  if (
    (commentType === "Reply To Comment" || commentType === "Reply To Reply") &&
    parentCommentId === null
  ) {
    throw valueError("parentCommentId is required when commentType is reply_comment");
  }
  if (
    (commentType === "reply_target" || commentType === "Reply To Chapter") &&
    parentCommentId !== null
  ) {
    throw valueError("parentCommentId must be empty when commentType is reply_target");
  }

  const userId = await resolveActorUserId(claims);
  return addCommentForTarget(userId, claims.role, {
    text: body.text,
    targetType,
    targetId,
    parentCommentId,
    commentType,
  });
});
