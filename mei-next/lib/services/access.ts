/**
 * Access enforcement — port of `services/access_service.py` (payments.md §7).
 * Pinned seam (CONVENTIONS.md `@/lib/services/access`):
 *
 * Precedence (reproduced exactly):
 * - `free`         → always allowed.
 * - `subscription` → `isSubscriptionActive`: `active === true` AND `expiresAt > now`.
 * - `paid`/default → `isChapterUnlocked`: legacy `user.unlockedChapters`
 *   membership OR an `entitlements` row for `(userId, chapterId)`.
 *
 * Gates page reads, reading-progress reads, and reactions.
 */
import { db } from "@/lib/db";
import { Entitlement, type ChapterDoc, type UserDoc } from "@/lib/models";

export type ChapterAccessType = "free" | "subscription" | "paid";

/** Mirrors LEGACY_STATUS_TO_ACCESS in `schemas/chapter_schema.py`. */
const LEGACY_STATUS_TO_ACCESS: Record<string, ChapterAccessType> = {
  free: "free",
  subscription: "subscription",
  paid: "paid",
  premium: "paid",
  locked: "paid",
};

/**
 * Resolve a raw chapter doc's effective accessType the way legacy ChapterOut
 * did: explicit accessType wins; else legacy `status` maps (premium/locked →
 * paid); unknown/missing → free.
 */
export function resolveChapterAccessType(chapter: ChapterDoc): ChapterAccessType {
  const access = chapter?.accessType;
  if (access === "free" || access === "subscription" || access === "paid") return access;
  const status = chapter?.status;
  if (status !== null && status !== undefined) {
    const mapped = LEGACY_STATUS_TO_ACCESS[String(status).trim().toLowerCase()];
    if (mapped) return mapped;
  }
  return "free";
}

/** Port of `is_subscription_active`: active flag AND a parseable future expiresAt. */
export function isSubscriptionActive(sub?: { active?: boolean; expiresAt?: string | null }): boolean {
  if (!sub) return false;
  if (!sub.active) return false;
  if (!sub.expiresAt) return false;
  const expiresAtMs = Date.parse(sub.expiresAt);
  if (Number.isNaN(expiresAtMs)) return false;
  return expiresAtMs > Date.now();
}

/**
 * Port of `is_chapter_unlocked`: legacy `unlockedChapters` array first, then
 * the `entitlements` collection (unique `(userId, chapterId)`).
 */
export async function isChapterUnlocked(user: UserDoc, chapterId: string): Promise<boolean> {
  const target = String(chapterId);
  const unlocked = user?.unlockedChapters;
  if (Array.isArray(unlocked) && unlocked.some((id) => String(id) === target)) {
    return true;
  }
  await db();
  const userId = String(user?._id ?? user?.userId ?? "");
  const found = await Entitlement.findOne({ userId, chapterId: target }, { _id: 1 }).lean();
  return found !== null;
}

/** Port of `has_chapter_access` — free / subscription / paid(default) precedence. */
export async function hasChapterAccess(user: UserDoc, chapter: ChapterDoc): Promise<boolean> {
  const accessType = resolveChapterAccessType(chapter);

  if (accessType === "free") return true;

  if (accessType === "subscription") {
    const sub = user?.subscription as { active?: boolean; expiresAt?: string | null } | null | undefined;
    return isSubscriptionActive(sub ?? undefined);
  }

  return isChapterUnlocked(user, String(chapter?._id ?? chapter?.id ?? ""));
}
