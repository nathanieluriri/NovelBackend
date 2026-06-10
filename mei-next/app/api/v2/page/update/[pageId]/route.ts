export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { require24, parseBody } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyAdminToken } from "@/lib/http/guards";
import { db } from "@/lib/db";
import { updatePageContent } from "@/lib/services/page";
import { invalidateSummaries } from "@/lib/cache/summary";

/** PageUpdateRequest: { textContent, status? }. */
const PageUpdateSchema = z.object({
  textContent: z.string(),
  status: z.string().nullish(),
});

/**
 * PATCH /api/v2/page/update/{pageId} — admin only. Recomputes textCount +
 * dateUpdated, recomputes the parent chapter, busts summary caches (page +
 * chapter). 404 "Resource already deleted" when the page is gone. Returns PageOut.
 */
export const PATCH = withRoute(async (req, ctx) => {
  const { pageId } = await ctx.params;
  require24(pageId, "pageId");

  await verifyAdminToken(req);
  const body = await parseBody(req, PageUpdateSchema);

  await db();
  const updated = await updatePageContent({
    pageId,
    textContent: body.textContent,
    status: body.status ?? null,
  });
  if (!updated) throw new HttpError(404, "Resource already deleted");

  await invalidateSummaries({
    pages: [updated.id],
    chapters: [updated.chapterId],
  });

  return updated;
});
