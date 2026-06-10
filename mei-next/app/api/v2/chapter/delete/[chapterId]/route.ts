export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { invalidateSummaries } from "@/lib/cache/summary";
import { deleteChapter } from "@/lib/services/chapter";

/**
 * DELETE /api/v2/chapter/delete/{chapterId} — admin. Cascades page deletion,
 * reorders remaining chapters, recomputes the parent book. Returns the deleted
 * `ChapterOut`. Busts the chapter + parent book summaries.
 */
export const DELETE = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { chapterId } = await ctx.params;

  const deleted = await deleteChapter(chapterId);

  await invalidateSummaries({ chapters: [deleted.id], books: [deleted.bookId] });
  return deleted;
});
