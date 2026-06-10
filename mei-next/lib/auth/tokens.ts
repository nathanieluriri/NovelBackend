import { Types } from "mongoose";
import { db } from "@/lib/db";
import { AccessToken, RefreshToken, type AccessTokenDoc } from "@/lib/models";
import { HttpError } from "@/lib/http/errors";
import { nowIso, isOlderThanDays } from "@/lib/util/dates";
import { signMemberJwt, signAdminJwt, decodeJwtIgnoreExpiry } from "./jwt";

/**
 * Stateful token lifecycle (port of ../security/tokens.py + ../security/auth.py
 * + ../repositories/tokens_repo.py — see auth.md §0/§2).
 *
 * - `accessToken` collection: member row `{userId, role:"member", dateCreated}`;
 *   admin row `{userId, role:"admin", status:"inactive", dateCreated}`. The row
 *   `_id` IS the opaque token carried inside the JWT's `accessToken` claim.
 * - `refreshToken` collection: `{userId, previousAccessToken, dateCreated}`.
 *   The refresh value handed to clients is the row `_id` (NOT a JWT).
 * - Rows older than 10 days are deleted ON READ (refresh-window enforcement).
 */

const STALE_AFTER_DAYS = 10;

/** Case-insensitive `Authorization: Bearer <jwt>` extraction. */
export function extractBearerToken(req: Request): string | null {
  const header = req.headers.get("authorization");
  if (!header) return null;
  const match = /^Bearer\s+(.+)$/i.exec(header.trim());
  if (!match) return null;
  const token = match[1].trim();
  return token || null;
}

function rowDateCreated(row: AccessTokenDoc): string | null {
  const dc = row.dateCreated;
  if (typeof dc === "string") return dc;
  if (dc instanceof Date) return dc.toISOString();
  return null;
}

/**
 * Port of `get_access_tokens`: row by inner id; stale rows (>10 days) are
 * DELETED on read. Admin rows gate on `status:"active"` and report "inactive".
 */
export async function getAccessTokenRow(
  innerId: string,
): Promise<AccessTokenDoc | "inactive" | null> {
  await db();
  if (!Types.ObjectId.isValid(innerId)) return null;
  const row = await AccessToken.findById(innerId).lean<AccessTokenDoc>();
  if (!row) return null;
  if (isOlderThanDays(rowDateCreated(row), STALE_AFTER_DAYS)) {
    await AccessToken.deleteOne({ _id: row._id });
    return null;
  }
  const role = row.role;
  if (role === "member") return row;
  if (role === "admin") {
    if (row.status === "active") return row;
    return "inactive";
  }
  return null;
}

/** Row exists, role is member, under 10 days. Null otherwise. */
export async function validateMemberAccessToken(innerId: string): Promise<AccessTokenDoc | null> {
  const row = await getAccessTokenRow(innerId);
  if (row && typeof row === "object" && row.role === "member") return row;
  return null;
}

/**
 * Row exists, role is admin, under 10 days. Returns the row when active,
 * "inactive" when not yet OTP-activated, null otherwise.
 */
export async function validateAdminAccessToken(
  innerId: string,
): Promise<AccessTokenDoc | "inactive" | null> {
  const row = await getAccessTokenRow(innerId);
  if (row === "inactive") return "inactive";
  if (row && typeof row === "object" && row.role === "admin") return row;
  return null;
}

async function createAccessRow(userId: string, role: "member" | "admin"): Promise<string> {
  const data: Record<string, unknown> = { userId, role, dateCreated: nowIso() };
  if (role === "admin") data.status = "inactive";
  const row = await AccessToken.create(data);
  return String(row._id);
}

async function createRefreshRow(userId: string, previousAccessToken: string): Promise<string> {
  const row = await RefreshToken.create({ userId, previousAccessToken, dateCreated: nowIso() });
  return String(row._id);
}

function assertValidUserId(userId: string): void {
  if (!Types.ObjectId.isValid(userId)) throw new HttpError(401, "Invalid User Id");
}

/** Issue (login/register/oauth-exchange): access row → member JWT → refresh row. */
export async function issueMemberTokens(
  userId: string,
): Promise<{ accessToken: string; refreshToken: string }> {
  await db();
  assertValidUserId(userId);
  const innerId = await createAccessRow(userId, "member");
  const accessToken = await signMemberJwt(innerId);
  const refreshToken = await createRefreshRow(userId, innerId);
  return { accessToken, refreshToken };
}

/** Admin variant — the access row is created `status:"inactive"` (OTP gates activation). */
export async function issueAdminTokens(
  userId: string,
): Promise<{ accessToken: string; refreshToken: string }> {
  await db();
  assertValidUserId(userId);
  const innerId = await createAccessRow(userId, "admin");
  const accessToken = await signAdminJwt(innerId);
  const refreshToken = await createRefreshRow(userId, innerId);
  return { accessToken, refreshToken };
}

/**
 * Full rotation (port of `verify_token_and_refresh_token` + the /refresh route):
 *  1. decode the (expired-OK) access JWT from the Authorization header;
 *  2. validate the old access row (expiry-tolerant; admin must not be inactive);
 *  3. validate the old refresh row and BIND it to the access token — it must
 *     exist, belong to the same user, and reference this access token as its
 *     `previousAccessToken`. (Hardening over legacy, which deleted the refresh
 *     row by id without binding. Reproduces the legacy contract for legitimate
 *     clients — a client always presents its own matching pair — while rejecting
 *     a forged/cross-account refresh that legacy would have accepted.)
 *  4. only after all checks pass: issue a NEW access row + JWT (+ activate it for
 *     admins) + NEW refresh row — so a failed validation never leaves orphan rows;
 *  5. delete the OLD access row and the OLD refresh row.
 */
export async function refreshTokens(
  req: Request,
  refreshToken: string,
): Promise<{ userId: string; dateCreated: string; refreshToken: string; accessToken: string }> {
  await db();
  const raw = extractBearerToken(req);
  if (!raw) throw new HttpError(401, "Invalid token");
  const claims = await decodeJwtIgnoreExpiry(raw);
  if (!claims) throw new HttpError(401, "Invalid Token");

  // --- validate the old access row (no minting yet) ---
  const role = claims.role;
  if (role !== "member" && role !== "admin") throw new HttpError(401, "Invalid Token");
  const oldRow = await getAccessTokenRow(claims.accessToken);
  if (role === "member") {
    if (!oldRow || typeof oldRow === "string" || oldRow.role !== "member") {
      throw new HttpError(404, "Couldn't Find Refresh Id");
    }
  } else {
    if (oldRow === "inactive") {
      throw new HttpError(401, "You Can't Make Use of an Inactive AccessToken");
    }
    if (!oldRow || typeof oldRow === "string" || oldRow.role !== "admin") {
      throw new HttpError(401, "Invalid Token");
    }
  }
  const userId = String(oldRow.userId);

  // --- validate + bind the old refresh row BEFORE minting (no orphan rows) ---
  if (!Types.ObjectId.isValid(refreshToken)) throw new HttpError(401, "Invalid Refresh Id");
  const refreshRow = await RefreshToken.findById(refreshToken).lean<{
    _id: unknown;
    userId?: unknown;
    previousAccessToken?: unknown;
  }>();
  if (!refreshRow) throw new HttpError(404, "Refresh Token is Invalid");
  if (
    String(refreshRow.userId) !== userId ||
    String(refreshRow.previousAccessToken) !== claims.accessToken
  ) {
    throw new HttpError(401, "Refresh Token is Invalid");
  }

  // --- all checks passed: mint the new pair, then revoke the old pair ---
  const newInnerId = await createAccessRow(userId, role);
  const newAccessJwt = role === "member" ? await signMemberJwt(newInnerId) : await signAdminJwt(newInnerId);
  if (role === "admin") {
    // Legacy activates the freshly rotated admin row immediately.
    await activateAdminToken(newInnerId);
  }
  const newRefreshId = await createRefreshRow(userId, newInnerId);
  await AccessToken.deleteOne({ _id: oldRow._id });
  await RefreshToken.deleteOne({ _id: refreshToken });

  return { userId, dateCreated: nowIso(), refreshToken: newRefreshId, accessToken: newAccessJwt };
}

/** Port of `delete_all_tokens_with_user_id` — logout everywhere (password change). */
export async function revokeAllTokensForUser(userId: string): Promise<void> {
  await db();
  await RefreshToken.deleteMany({ userId });
  await AccessToken.deleteMany({ userId });
}

/** Port of `update_admin_access_tokens` — flips the admin row to status:"active". */
export async function activateAdminToken(innerId: string): Promise<void> {
  await db();
  if (!Types.ObjectId.isValid(innerId)) throw new HttpError(401, "Invalid Access Id");
  await AccessToken.findByIdAndUpdate(innerId, { $set: { status: "active" } });
}
