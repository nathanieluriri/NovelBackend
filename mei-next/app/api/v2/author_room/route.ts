export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyToken, verifyAnyToken } from "@/lib/http/guards";
import { getAccessTokenRow, type Claims } from "@/lib/auth";
import {
  retrieveAuthorRooms,
  retrieveAuthorRoomsCount,
  addAuthorRoom,
} from "@/lib/services/authorRoom";

/** AuthorRoomBase — `{ text, chapterId }` (schema.md §5; no extra validators). */
const AuthorRoomBase = z.object({
  text: z.string(),
  chapterId: z.string(),
});

/**
 * Resolve the calling member's userId off the access-token row — the port of
 * legacy `_get_member_user_id_or_401` (`get_access_tokens(...)` → `token.userId`,
 * 401 "Invalid token" otherwise).
 */
async function memberUserIdOr401(claims: Claims): Promise<string> {
  const row = await getAccessTokenRow(claims.accessToken);
  if (!row || typeof row === "string") throw new HttpError(401, "Invalid token");
  const userId = String(row.userId ?? "");
  if (!userId) throw new HttpError(401, "Invalid token");
  return userId;
}

/**
 * GET /api/v2/author_room/ — member.
 * Query: `skip=0,limit=20`. Returns `PaginatedListOut[AuthorRoomOut]` (flat
 * items) scoped by the caller's userId (used to hydrate `userReaction`). Port of
 * `list_author_rooms`.
 */
export const GET = withRoute(async (req) => {
  const claims = await verifyToken(req);
  const { skip, limit } = parseSkipLimit(req);

  const userId = await memberUserIdOr401(claims);
  const [items, total] = await Promise.all([
    retrieveAuthorRooms(skip, limit, userId),
    retrieveAuthorRoomsCount(),
  ]);
  return paginate(items, skip, limit, total);
});

/**
 * POST /api/v2/author_room/ — member OR admin (`verify_any_token`).
 * Body: `AuthorRoomBase { text, chapterId }`. Returns `AuthorRoomOut` (201).
 * Port of `create_a_comment_in_author_room`.
 */
export const POST = withRoute(
  async (req) => {
    await verifyAnyToken(req);
    const body = await parseBody(req, AuthorRoomBase);
    return addAuthorRoom(body);
  },
  { status: 201 },
);
