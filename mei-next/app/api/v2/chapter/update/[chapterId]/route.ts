export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { invalidateSummaries } from "@/lib/cache/summary";
import { updateChapter } from "@/lib/services/chapter";

/**
 * PATCH /api/v2/chapter/update/{chapterId} — admin. Body
 * `ChapterUpdateStatusOrLabelRequest`. Returns `ChapterOut`. Busts the chapter
 * + parent book summaries.
 *
 * The legacy `status`→`accessType` mapping and the unlockBundleId bundle rules
 * (the `mode='after'` ValueError → 422) live in `updateChapter` so the same
 * rules apply whether the value came from the body or the stored doc.
 */
const chapterUpdateRequest = z.object({
  chapterLabel: z.string().nullish(),
  status: z.string().nullish(),
  accessType: z.enum(["free", "subscription", "paid"]).nullish(),
  unlockBundleId: z.string().nullish(),
  coverImage: z.string().nullish(),
});

export const PATCH = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { chapterId } = await ctx.params;
  const body = await parseBody(req, chapterUpdateRequest);

  const updated = await updateChapter(chapterId, {
    chapterLabel: body.chapterLabel ?? null,
    status: body.status ?? null,
    accessType: body.accessType ?? null,
    unlockBundleId: body.unlockBundleId ?? null,
    coverImage: body.coverImage ?? null,
  });

  await invalidateSummaries({ chapters: [updated.id], books: [updated.bookId] });
  return updated;
});
