export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyAnyToken } from "@/lib/http/guards";
import {
  resolveActorUserId,
  createBookmarkForTarget,
} from "@/lib/services/bookmark";
import type { InteractionTargetType } from "@/lib/serializers";

/**
 * POST /api/v2/bookmark/create — member OR admin. Body `BookMarkCreateRequest`.
 * Returns `BookMarkOutAsync`. Port of `create_new_bookmark` +
 * `create_bookmark_for_target`.
 *
 * Validators mirror `BookMarkCreateRequest` (schema.md §5 / bookmark_schema.py):
 *  - before: legacy `pageId`-only payload (no targetType/targetId) → targetType
 *    "page", targetId = pageId.
 *  - after: targetType AND targetId required (else ValueError); targetId must be
 *    exactly 24 chars (else ValueError). Both surface as Pydantic-shaped 422s.
 */

const bookMarkCreateRequest = z.object({
  targetType: z.enum(["book", "chapter", "page"]).nullish(),
  targetId: z.string().nullish(),
  pageId: z.string().nullish(),
});

function valueError(msg: string): HttpError {
  return new HttpError(422, "Validation failed", [
    { type: "value_error", loc: ["body"], msg: `Value error, ${msg}`, input: null },
  ]);
}

export const POST = withRoute(async (req) => {
  const claims = await verifyAnyToken(req);
  const body = await parseBody(req, bookMarkCreateRequest);

  // before-validator: legacy pageId-only normalization.
  let targetType: InteractionTargetType | null = body.targetType ?? null;
  let targetId: string | null = body.targetId ?? null;
  const pageId = body.pageId ?? null;
  if (targetType === null && targetId === null && pageId !== null) {
    targetType = "page";
    targetId = pageId;
  }

  // after-validator.
  if (targetType === null || targetId === null) {
    throw valueError("targetType and targetId are required");
  }
  if (targetId.length !== 24) {
    throw valueError("targetId must be exactly 24 characters long");
  }

  const userId = await resolveActorUserId(claims);
  return createBookmarkForTarget(userId, { targetType, targetId, pageId });
});
