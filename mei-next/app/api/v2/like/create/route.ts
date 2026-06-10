export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAnyToken } from "@/lib/http/guards";
import { resolveActorUserId, addLike } from "@/lib/services/like";

/** LikeBaseRequest — `{ chapterId }` (schema.md §5; no extra validators). */
const LikeBaseRequest = z.object({
  chapterId: z.string(),
});

/**
 * POST /api/v2/like/create — member OR admin.
 * Body: `LikeBaseRequest { chapterId }`. Returns `LikeOut`. The chapter must
 * exist (404 "Chapter not found"); the like is idempotent on `{userId,chapterId}`.
 * `role` is taken from the JWT claim, `userId` from the access-token row — exactly
 * as legacy `like_chapter`. Port of `like_chapter`.
 */
export const POST = withRoute(async (req) => {
  const claims = await verifyAnyToken(req);
  const body = await parseBody(req, LikeBaseRequest);

  const userId = await resolveActorUserId(claims);
  return addLike(userId, claims.role, body.chapterId);
});
