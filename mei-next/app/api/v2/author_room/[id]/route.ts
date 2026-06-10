export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyToken, verifyAnyToken, verifyAdminToken } from "@/lib/http/guards";
import { getAccessTokenRow, type Claims } from "@/lib/auth";
import {
  retrieveAuthorRoomById,
  updateAuthorRoomById,
  removeAuthorRoom,
} from "@/lib/services/authorRoom";

/** AuthorRoomUpdate — `{ text }` (schema.md §5). */
const AuthorRoomUpdate = z.object({
  text: z.string(),
});

/** Port of legacy `_get_member_user_id_or_401` — 401 "Invalid token" on failure. */
async function memberUserIdOr401(claims: Claims): Promise<string> {
  const row = await getAccessTokenRow(claims.accessToken);
  if (!row || typeof row === "string") throw new HttpError(401, "Invalid token");
  const userId = String(row.userId ?? "");
  if (!userId) throw new HttpError(401, "Invalid token");
  return userId;
}

/**
 * GET /api/v2/author_room/{id} — member.
 * Returns `AuthorRoomOut` (404 when missing, 400 on a malformed id). The caller's
 * userId hydrates `userReaction`. Port of `get_author_room_by_id`.
 */
export const GET = withRoute(async (req, ctx) => {
  const claims = await verifyToken(req);
  const { id } = await ctx.params;
  const userId = await memberUserIdOr401(claims);
  return retrieveAuthorRoomById(id, userId);
});

/**
 * PATCH /api/v2/author_room/{id} — member OR admin (`verify_any_token`).
 * Body: `AuthorRoomUpdate { text }`. Returns `AuthorRoomOut` (404 when missing,
 * 400 on a malformed id). Port of `update_a_comment_in_author_room`.
 */
export const PATCH = withRoute(async (req, ctx) => {
  await verifyAnyToken(req);
  const { id } = await ctx.params;
  const body = await parseBody(req, AuthorRoomUpdate);
  return updateAuthorRoomById(id, body);
});

/**
 * DELETE /api/v2/author_room/{id} — ADMIN ONLY.
 * Returns `{deleted:true}` (200); 404 when missing, 400 on a malformed id.
 * Port of `delete_a_comment_in_author_room`, hardened: the legacy route was
 * unauthenticated (anyone could delete any author room). Author rooms are
 * admin/author content (no per-user owner in the schema), so deletion now
 * requires an admin token. This is the one intentional auth deviation from
 * legacy parity, approved to close an open destructive endpoint.
 */
export const DELETE = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { id } = await ctx.params;
  await removeAuthorRoom(id);
  return { deleted: true };
});
