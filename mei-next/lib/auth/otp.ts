import { randomInt } from "node:crypto";

import { redis } from "@/lib/redis";

/**
 * OTP flows (port of ../security/user_otp.py + ../security/admin_otp.py —
 * see auth.md §5). Redis-backed, TTL 380s, 6 NON-REPEATING digits.
 *
 * Two deliberately reversed key/value layouts:
 *  - user/admin password reset:  key = otp,      value = email
 *  - admin login activation:     key = adminJWT, value = otp
 *
 * Uses the raw redis() client (NOT the best-effort helpers) — OTP storage
 * failures must surface, not degrade silently. @upstash/redis auto-deserializes
 * on read (an all-digit OTP can come back as a number), so comparisons go
 * through String(...).
 */

const OTP_TTL_SECONDS = 380;
const OTP_LENGTH = 6;

/** 6 DISTINCT digits — `random.sample(range(0, 10), 6)` joined. CSPRNG-backed. */
export function generateOtp(): string {
  const digits = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
  // Fisher-Yates shuffle, then take the first 6 (sample without replacement).
  for (let i = digits.length - 1; i > 0; i--) {
    const j = randomInt(0, i + 1);
    const tmp = digits[i];
    digits[i] = digits[j];
    digits[j] = tmp;
  }
  return digits.slice(0, OTP_LENGTH).join("");
}

/** Password-reset layout: `setex(key=otp, value=email, 380)`. */
export async function storeUserOtp(email: string, otp: string): Promise<void> {
  await redis().set(otp, email, { ex: OTP_TTL_SECONDS });
}

/** `get(otp) === email` → delete the key, true. False otherwise (missing/mismatch). */
export async function verifyUserOtp(email: string, otp: string): Promise<boolean> {
  const value = await redis().get<unknown>(otp);
  if (value === null || value === undefined) return false;
  if (String(value) !== email) return false;
  await redis().del(otp);
  return true;
}

/** Admin login-activation layout (REVERSED): `setex(key=adminJWT, value=otp, 380)`. */
export async function storeAdminLoginOtp(adminJwt: string, otp: string): Promise<void> {
  await redis().set(adminJwt, otp, { ex: OTP_TTL_SECONDS });
}

/** `get(adminJWT) === otp` → delete the key, true. False otherwise. */
export async function verifyAdminLoginOtp(adminJwt: string, otp: string): Promise<boolean> {
  const value = await redis().get<unknown>(adminJwt);
  if (value === null || value === undefined) return false;
  if (String(value) !== otp) return false;
  await redis().del(adminJwt);
  return true;
}
