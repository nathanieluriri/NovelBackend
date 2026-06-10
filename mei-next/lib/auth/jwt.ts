import { SignJWT, jwtVerify, decodeProtectedHeader } from "jose";
import { Types } from "mongoose";
import { db } from "@/lib/db";
import { requireEnv } from "@/lib/env";

/**
 * HS256 JWT with DB-backed key rotation (port of ../security/encrypting_jwt.py).
 *
 * Key source is NON-STANDARD: `db.secret_keys.findOne({_id: ObjectId(SECRETID)})`
 * minus `_id` is a map `{ kid: secret, ... }`. Signing picks a key AT RANDOM and
 * puts its name in the protected header `kid`; verification reads `kid` from the
 * (unverified) header and resolves the matching secret.
 *
 * NOTE: despite the legacy file name, nothing is encrypted — HS256 signing only.
 *
 * Payload (frontend-load-bearing, see auth.md §1):
 *   { "accessToken": "<24-hex inner id>", "role": "member"|"admin", "exp": <unix> }
 */

export type Claims = { accessToken: string; role: "member" | "admin"; exp: number };

const ACCESS_JWT_TTL = "15m";
const KEY_CACHE_TTL_MS = 60_000; // short in-memory TTL, refetched lazily

let keyCache: { keys: Record<string, string>; fetchedAt: number } | null = null;

async function fetchSecretMap(): Promise<Record<string, string>> {
  const secretId = requireEnv("SECRETID");
  const conn = await db();
  const col = conn.connection.db?.collection("secret_keys");
  if (!col) throw new Error("Mongo connection has no native db handle");
  const doc = await col.findOne({ _id: new Types.ObjectId(secretId) });
  if (!doc) throw new Error("secret_keys document not found");
  const keys: Record<string, string> = {};
  for (const [k, v] of Object.entries(doc)) {
    if (k === "_id") continue;
    if (typeof v === "string" && v) keys[k] = v;
  }
  if (Object.keys(keys).length === 0) throw new Error("secret_keys document has no usable keys");
  return keys;
}

async function getSecretMap(forceRefresh = false): Promise<Record<string, string>> {
  if (!forceRefresh && keyCache && Date.now() - keyCache.fetchedAt < KEY_CACHE_TTL_MS) {
    return keyCache.keys;
  }
  const keys = await fetchSecretMap();
  keyCache = { keys, fetchedAt: Date.now() };
  return keys;
}

async function signJwt(innerId: string, role: "member" | "admin"): Promise<string> {
  const keys = await getSecretMap();
  const kids = Object.keys(keys);
  const kid = kids[Math.floor(Math.random() * kids.length)];
  const secret = keys[kid];
  return new SignJWT({ accessToken: innerId, role })
    .setProtectedHeader({ alg: "HS256", typ: "JWT", kid })
    .setExpirationTime(ACCESS_JWT_TTL)
    .sign(new TextEncoder().encode(secret));
}

export async function signMemberJwt(innerId: string): Promise<string> {
  return signJwt(innerId, "member");
}

export async function signAdminJwt(innerId: string): Promise<string> {
  return signJwt(innerId, "admin");
}

/** Resolve the HMAC secret for a token via its (unverified) header `kid`. */
async function resolveSecret(token: string): Promise<Uint8Array | null> {
  let kid: string | undefined;
  try {
    kid = decodeProtectedHeader(token).kid;
  } catch {
    return null; // malformed token
  }
  if (!kid) return null;
  let keys = await getSecretMap();
  let secret = keys[kid];
  if (!secret) {
    // kid may have been rotated in since our last fetch — refresh once.
    keys = await getSecretMap(true);
    secret = keys[kid];
  }
  if (!secret) return null; // unknown key ID
  return new TextEncoder().encode(secret);
}

function toClaims(payload: Record<string, unknown>): Claims | null {
  const accessToken = payload.accessToken;
  if (typeof accessToken !== "string" || !accessToken) return null;
  const role = typeof payload.role === "string" ? payload.role : "";
  const exp = typeof payload.exp === "number" ? payload.exp : 0;
  // role kept loose on purpose: verifyAnyToken must be able to reject unknown
  // roles with the legacy "Invalid token Type" message.
  return { accessToken, role: role as Claims["role"], exp };
}

/** Verify signature + expiry. Returns null on any invalid/expired token. */
export async function decodeJwt(token: string): Promise<Claims | null> {
  const secret = await resolveSecret(token);
  if (!secret) return null;
  try {
    const { payload } = await jwtVerify(token, secret, { algorithms: ["HS256"] });
    return toClaims(payload);
  } catch {
    return null;
  }
}

/**
 * Verify the signature but tolerate an expired `exp` (refresh flow — the client
 * presents an expired access JWT there). Still null on bad signature/malformed.
 */
export async function decodeJwtIgnoreExpiry(token: string): Promise<Claims | null> {
  const secret = await resolveSecret(token);
  if (!secret) return null;
  try {
    const { payload } = await jwtVerify(token, secret, { algorithms: ["HS256"] });
    return toClaims(payload);
  } catch (err) {
    if ((err as { code?: string } | null)?.code !== "ERR_JWT_EXPIRED") return null;
    try {
      const { payload } = await jwtVerify(token, secret, {
        algorithms: ["HS256"],
        clockTolerance: 60 * 60 * 24 * 365 * 1000, // effectively ignore exp
      });
      return toClaims(payload);
    } catch {
      return null;
    }
  }
}
