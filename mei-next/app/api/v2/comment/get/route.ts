export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { HttpError } from "@/lib/http/errors";
import { verifyAnyToken } from "@/lib/http/guards";
import {
  resolveActorUserId,
  retrieveTargetComments,
  retrieveTargetCommentsCount,
  retrieveUserComments,
  retrieveUserCommentsCount,
} from "@/lib/services/comment";
import type { InteractionTargetType } from "@/lib/serializers";

/**
 * GET /api/v2/comment/get — member OR admin.
 * Query: `targetType?`, `targetId?`, `skip=0,limit=20`. When BOTH targetType and
 * targetId are supplied → that target's comments; supplying only one → 400. When
 * neither is supplied → the caller's own comments. Returns
 * `PaginatedListOut[CommentOut]` (flat items). Port of `get_comments_v2`.
 */

const TARGET_TYPES: readonly string[] = ["book", "chapter", "page"];

export const GET = withRoute(async (req) => {
  const claims = await verifyAnyToken(req);
  const { skip, limit } = parseSkipLimit(req);
  const sp = new URL(req.url).searchParams;
  const rawTargetType = sp.get("targetType");
  const targetId = sp.get("targetId");

  // Legacy FastAPI coerced targetType via the InteractionTargetType enum (422 on
  // an invalid value); a missing param is null.
  let targetType: InteractionTargetType | null = null;
  if (rawTargetType !== null) {
    if (!TARGET_TYPES.includes(rawTargetType)) {
      throw new HttpError(422, "targetType must be one of: book, chapter, page");
    }
    targetType = rawTargetType as InteractionTargetType;
  }

  if (targetType !== null || targetId !== null) {
    if (targetType === null || targetId === null) {
      throw new HttpError(400, "targetType and targetId must be provided together");
    }
    const [items, total] = await Promise.all([
      retrieveTargetComments(targetType, targetId, skip, limit),
      retrieveTargetCommentsCount(targetType, targetId),
    ]);
    return paginate(items, skip, limit, total);
  }

  const userId = await resolveActorUserId(claims);
  const [items, total] = await Promise.all([
    retrieveUserComments(userId, skip, limit),
    retrieveUserCommentsCount(userId),
  ]);
  return paginate(items, skip, limit, total);
});
