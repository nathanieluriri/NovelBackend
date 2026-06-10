export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { require24 } from "@/lib/http/validate";
import { HttpError } from "@/lib/http/errors";
import { verifyAdminToken } from "@/lib/http/guards";
import { db } from "@/lib/db";
import { deletePage } from "@/lib/services/page";
import { invalidateSummaries } from "@/lib/cache/summary";

/**
 * DELETE /api/v2/page/delete/{pageId} — admin only. 404 "Resource already
 * deleted" when the page is gone. Recomputes the parent chapter and busts
 * summary caches (page + chapter). Returns the deleted PageOut (legacy parity).
 */
export const DELETE = withRoute(async (req, ctx) => {
  const { pageId } = await ctx.params;
  require24(pageId, "pageId");

  await verifyAdminToken(req);
  await db();

  const deleted = await deletePage(pageId);
  if (!deleted) throw new HttpError(404, "Resource already deleted");

  await invalidateSummaries({
    pages: [deleted.id],
    chapters: [deleted.chapterId],
  });

  return deleted;
});
