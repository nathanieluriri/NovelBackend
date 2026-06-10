import { Types } from "mongoose";
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { decodeJwt, type Claims } from "@/lib/auth/jwt";
import {
  extractBearerToken,
  getAccessTokenRow,
  validateAdminAccessToken,
  validateMemberAccessToken,
} from "@/lib/auth/tokens";
import { User, type UserDoc } from "@/lib/models";

/**
 * HTTP auth guards (port of ../security/auth.py — see auth.md §4).
 *
 * Auth is STATEFUL: a valid JWT signature is NOT enough — the inner id must
 * resolve to a live `accessToken` row (< 10 days old; admins additionally
 * `status:"active"`). Token travels on `Authorization: Bearer <jwt>` (header,
 * never cookie); extraction is case-insensitive.
 *
 * Missing/malformed header replicates FastAPI `HTTPBearer(auto_error=True)`
 * (../security/auth.py): absent header → 403 "Not authenticated"; present but
 * non-Bearer scheme → 403 "Invalid authentication credentials". A PRESENT but
 * invalid/expired token keeps the legacy 401 messages below.
 */

/** Legacy HTTPBearer behavior for an absent/non-Bearer Authorization header. */
function missingBearerError(req: Request): HttpError {
  return req.headers.get("authorization")
    ? new HttpError(403, "Invalid authentication credentials")
    : new HttpError(403, "Not authenticated");
}

/** Member guard — 401 "Invalid token" for a present-but-invalid token. */
export async function verifyToken(req: Request): Promise<Claims> {
  const raw = extractBearerToken(req);
  if (!raw) throw missingBearerError(req);
  const claims = await decodeJwt(raw);
  if (!claims || claims.role !== "member") throw new HttpError(401, "Invalid token");
  const row = await validateMemberAccessToken(claims.accessToken);
  if (!row) throw new HttpError(401, "Invalid token");
  return claims;
}

/**
 * Admin guard — exact legacy 401 variants:
 *  - invalid/expired JWT          → "Access Token Expired"
 *  - wrong role / row missing     → "Invalid admin token"
 *  - row not yet OTP-activated    → "Admin Token hasn't been activated"
 */
export async function verifyAdminToken(req: Request): Promise<Claims> {
  const raw = extractBearerToken(req);
  if (!raw) throw missingBearerError(req);
  const claims = await decodeJwt(raw);
  // Legacy: an expired/invalid JWT surfaces as a TypeError caught as
  // "Access Token Expired" in verify_admin_token.
  if (!claims) throw new HttpError(401, "Access Token Expired");
  if (claims.role !== "admin") throw new HttpError(401, "Invalid admin token");
  const result = await validateAdminAccessToken(claims.accessToken);
  if (result === "inactive") throw new HttpError(401, "Admin Token hasn't been activated");
  if (!result) throw new HttpError(401, "Invalid admin token");
  return claims;
}

/** Member OR admin — dispatch on the JWT's `role` claim (legacy messages kept). */
export async function verifyAnyToken(req: Request): Promise<Claims> {
  const raw = extractBearerToken(req);
  if (!raw) throw missingBearerError(req);
  const claims = await decodeJwt(raw);
  if (!claims) throw new HttpError(401, "Invalid Token");
  if (claims.role === "admin") return verifyAdminToken(req);
  if (claims.role === "member") return verifyToken(req);
  throw new HttpError(401, "Invalid token Type");
}

/** Session row → userId → User doc. 401 when any link of the chain is gone. */
export async function getUserFromClaims(claims: Claims): Promise<UserDoc> {
  await db();
  const row = await getAccessTokenRow(claims.accessToken);
  if (!row || typeof row === "string") throw new HttpError(401, "Invalid token");
  const userId = String(row.userId ?? "");
  if (!Types.ObjectId.isValid(userId)) throw new HttpError(401, "Invalid token");
  const user = await User.findById(userId).lean<UserDoc>();
  if (!user) throw new HttpError(401, "Invalid token");
  return user;
}

/**
 * Resolve the requesting reader: admin claims → role "admin" with user null;
 * member claims → load the access row, its userId, then the User doc.
 */
export async function resolveReader(
  claims: Claims,
): Promise<{ role: "member" | "admin"; user: UserDoc | null }> {
  if (claims.role === "admin") return { role: "admin", user: null };
  const user = await getUserFromClaims(claims);
  return { role: "member", user };
}
