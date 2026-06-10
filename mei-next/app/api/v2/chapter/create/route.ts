export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyAdminToken } from "@/lib/http/guards";
import { invalidateSummaries } from "@/lib/cache/summary";
import { createChapter } from "@/lib/services/chapter";

/**
 * POST /api/v2/chapter/create — admin. Body `ChapterBaseRequest`. Returns
 * `ChapterOut`. Busts the new chapter + parent book summaries.
 *
 * Validators mirror `ChapterBaseRequest` (schema.md §5 / chapter_schema.py):
 *  - legacy `status` → `accessType` (premium/locked → paid; unknown/missing → free)
 *  - accessType "paid" REQUIRES unlockBundleId
 *  - accessType "free"/"subscription" must NOT set unlockBundleId
 * The two bundle rules are the legacy `model_validator(mode='after')` ValueError
 * → reproduced as a Pydantic-shaped 422 (`type:"value_error"`).
 */

const LEGACY_STATUS_TO_ACCESS: Record<string, "free" | "subscription" | "paid"> = {
  free: "free",
  subscription: "subscription",
  paid: "paid",
  premium: "paid",
  locked: "paid",
};

type AccessType = "free" | "subscription" | "paid";

const chapterBaseRequest = z.object({
  bookId: z.string(),
  chapterLabel: z.string(),
  status: z.string().nullish(),
  accessType: z.enum(["free", "subscription", "paid"]).nullish(),
  unlockBundleId: z.string().nullish(),
  coverImage: z.string().nullish(),
});

/** ChapterBaseRequest before-validator: accessType wins; else map status; else free. */
function resolveAccess(accessType: AccessType | null | undefined, status: string | null | undefined): AccessType {
  if (accessType) return accessType;
  if (status !== null && status !== undefined) {
    return LEGACY_STATUS_TO_ACCESS[String(status).trim().toLowerCase()] ?? "free";
  }
  return "free";
}

/** ChapterBaseRequest after-validator (ValueError → 422 "value_error"). */
function validateBundleRules(access: AccessType, unlockBundleId: string | null | undefined): void {
  if (access === "paid" && !unlockBundleId) {
    throw new HttpError(422, "Validation failed", [
      { type: "value_error", loc: ["body"], msg: "Value error, unlockBundleId is required when accessType is paid", input: null },
    ]);
  }
  if ((access === "free" || access === "subscription") && unlockBundleId !== null && unlockBundleId !== undefined) {
    throw new HttpError(422, "Validation failed", [
      { type: "value_error", loc: ["body"], msg: "Value error, unlockBundleId must be empty unless accessType is paid", input: null },
    ]);
  }
}

export const POST = withRoute(async (req) => {
  await verifyAdminToken(req);
  const body = await parseBody(req, chapterBaseRequest);

  const accessType = resolveAccess(body.accessType, body.status);
  validateBundleRules(accessType, body.unlockBundleId);

  const created = await createChapter({
    bookId: body.bookId,
    chapterLabel: body.chapterLabel,
    status: body.status ?? null,
    accessType,
    unlockBundleId: body.unlockBundleId ?? null,
    coverImage: body.coverImage ?? null,
  });

  await invalidateSummaries({ chapters: [created.id], books: [created.bookId] });
  return created;
});
