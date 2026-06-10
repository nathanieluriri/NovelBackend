import { Redis } from "@upstash/redis";

/**
 * Upstash Redis client (OTP store + entity-summary cache).
 * All helpers are BEST-EFFORT: Redis failures degrade silently — they must
 * never break a request (see ../nextjs-migration/caching.md).
 */
let _redis: Redis | null = null;

export function redis(): Redis {
  if (!_redis) _redis = Redis.fromEnv();
  return _redis;
}

export async function rGet(key: string): Promise<string | null> {
  try {
    const v = await redis().get(key);
    if (v === null || v === undefined) return null;
    return typeof v === "string" ? v : JSON.stringify(v);
  } catch {
    return null;
  }
}

export async function rSetEx(key: string, ttlSeconds: number, value: string): Promise<void> {
  try {
    await redis().set(key, value, { ex: ttlSeconds });
  } catch {
    /* best-effort */
  }
}

export async function rDel(...keys: string[]): Promise<void> {
  if (!keys.length) return;
  try {
    await redis().del(...keys);
  } catch {
    /* best-effort */
  }
}
