import bcrypt from "bcryptjs";

/**
 * Password hashing (port of ../security/hash.py — see auth.md §3).
 * bcrypt cost 12 (the Python `gensalt()` default), so existing stored hashes
 * keep working. Only `provider:"credentials"` users have a password; google
 * users store null.
 */

const BCRYPT_COST = 12;

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, BCRYPT_COST);
}

/**
 * Legacy Python stored bcrypt hashes as BYTES, so Mongo may hold either a
 * plain string or a BSON Binary. Normalize both before comparing.
 */
function normalizeStoredHash(hashed: unknown): string | null {
  if (typeof hashed === "string") return hashed || null;
  if (hashed === null || hashed === undefined) return null;
  if (hashed instanceof Uint8Array) return Buffer.from(hashed).toString("utf8");
  if (typeof hashed === "object") {
    // BSON Binary exposes its bytes on `.buffer`.
    const buf = (hashed as { buffer?: unknown }).buffer;
    if (buf instanceof Uint8Array) return Buffer.from(buf).toString("utf8");
    if (buf instanceof ArrayBuffer) return Buffer.from(buf).toString("utf8");
    const s = String(hashed);
    return s && s !== "[object Object]" ? s : null;
  }
  return null;
}

export async function checkPassword(password: string, hashed: unknown): Promise<boolean> {
  const normalized = normalizeStoredHash(hashed);
  if (!normalized) return false;
  try {
    return await bcrypt.compare(password, normalized);
  } catch {
    return false;
  }
}
