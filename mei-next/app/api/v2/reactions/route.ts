export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyToken } from "@/lib/http/guards";
import { getAccessTokenRow, type Claims } from "@/lib/auth";
import {
  retrieveReactions,
  retrieveReactionsCount,
  addReaction,
} from "@/lib/services/reaction";

/**
 * ReactionBase — `{ reaction, authorRoomId }` (schema.md §5). `reaction` is
 * trimmed and must be non-empty (legacy `ReactionBase.normalize_reaction`); an
 * empty/whitespace value → 422. (userId is taken from the caller's session, not
 * the body.)
 */
const ReactionBase = z.object({
  reaction: z
    .string()
    .transform((s) => s.trim())
    .refine((s) => s.length > 0, { message: "reaction must not be empty" }),
  authorRoomId: z.string(),
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
 * GET /api/v2/reactions/ — PUBLIC (no auth, exactly as legacy `list_reactions`).
 * Query: `skip=0,limit=20`. Returns `PaginatedListOut[ReactionOut]` (flat items).
 */
export const GET = withRoute(async (req) => {
  const { skip, limit } = parseSkipLimit(req);
  const [items, total] = await Promise.all([
    retrieveReactions(skip, limit),
    retrieveReactionsCount(),
  ]);
  return paginate(items, skip, limit, total);
});

/**
 * POST /api/v2/reactions/ — member.
 * Body: `ReactionBase { reaction, authorRoomId }`; `userId` comes from the
 * session. Returns `ReactionOut` (201). The legacy `APIResponse` shape is
 * returned so its `detail` ("Reaction created successfully") becomes the
 * envelope `message` (withRoute unwraps it). Port of `create_reaction`.
 */
export const POST = withRoute(
  async (req) => {
    const claims = await verifyToken(req);
    const body = await parseBody(req, ReactionBase);
    const userId = await memberUserIdOr401(claims);
    const created = await addReaction({ ...body, userId });
    return { status_code: 201, data: created, detail: "Reaction created successfully" };
  },
  { status: 201 },
);
