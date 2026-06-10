export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyToken } from "@/lib/http/guards";
import { getAccessTokenRow, type Claims } from "@/lib/auth";
import {
  retrieveReactionByUserAndRoom,
  updateReactionByUserAndRoom,
  removeReactionForUser,
} from "@/lib/services/reaction";

/**
 * ReactionUpdate — `{ reaction?, last_updated(auto) }` (schema.md §5). When
 * present, `reaction` is trimmed non-empty (422 otherwise); a null `reaction`
 * surfaces downstream as 400 "reaction is required" (legacy
 * `update_reaction_by_id`). `last_updated` is set server-side, not from the body.
 */
const ReactionUpdate = z.object({
  reaction: z
    .string()
    .transform((s) => s.trim())
    .refine((s) => s.length > 0, { message: "reaction must not be empty" })
    .nullish(),
});

/** Port of legacy `_get_member_user_id` — 401 "Invalid token" on failure. */
async function memberUserIdOr401(claims: Claims): Promise<string> {
  const row = await getAccessTokenRow(claims.accessToken);
  if (!row || typeof row === "string") throw new HttpError(401, "Invalid token");
  const userId = String(row.userId ?? "");
  if (!userId) throw new HttpError(401, "Invalid token");
  return userId;
}

/**
 * GET /api/v2/reactions/{authorRoomId} — member.
 * Returns the caller's `ReactionOut` (404 when absent). The legacy `APIResponse`
 * shape is returned so its `detail` ("Reaction fetched") becomes the envelope
 * `message`. Port of `get_reaction_for_room`.
 */
export const GET = withRoute(async (req, ctx) => {
  const claims = await verifyToken(req);
  const { authorRoomId } = await ctx.params;
  const userId = await memberUserIdOr401(claims);
  const item = await retrieveReactionByUserAndRoom(userId, authorRoomId);
  return { status_code: 200, data: item, detail: "Reaction fetched" };
});

/**
 * PATCH /api/v2/reactions/{authorRoomId} — member.
 * Body: `ReactionUpdate { reaction? }`. Returns the updated `ReactionOut`. The
 * legacy `APIResponse` `detail` ("Reaction updated successfully") becomes the
 * envelope `message`. Port of `update_reaction`.
 */
export const PATCH = withRoute(async (req, ctx) => {
  const claims = await verifyToken(req);
  const { authorRoomId } = await ctx.params;
  const body = await parseBody(req, ReactionUpdate);
  const userId = await memberUserIdOr401(claims);
  const updated = await updateReactionByUserAndRoom(userId, authorRoomId, {
    reaction: body.reaction ?? null,
  });
  return { status_code: 200, data: updated, detail: "Reaction updated successfully" };
});

/**
 * DELETE /api/v2/reactions/{authorRoomId} — member.
 * Deletes the caller's reaction; returns `null` data. The legacy `APIResponse`
 * `detail` ("Reaction deleted successfully") becomes the envelope `message`.
 * Port of `delete_reaction`.
 */
export const DELETE = withRoute(async (req, ctx) => {
  const claims = await verifyToken(req);
  const { authorRoomId } = await ctx.params;
  const userId = await memberUserIdOr401(claims);
  await removeReactionForUser(userId, authorRoomId);
  return { status_code: 200, data: null, detail: "Reaction deleted successfully" };
});
