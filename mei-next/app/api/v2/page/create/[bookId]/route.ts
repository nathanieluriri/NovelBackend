export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { require24, parseBody } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { db } from "@/lib/db";
import { addPage } from "@/lib/services/page";
import { invalidateSummaries } from "@/lib/cache/summary";

/** PageBase (create): { chapterId, textContent, status }. */
const PageBaseSchema = z.object({
  chapterId: z.string(),
  textContent: z.string(),
  status: z.string(),
});

/**
 * POST /api/v2/page/create/{bookId} — admin only. Creates a page, recomputes
 * the parent chapter, busts summary caches (book + page + chapter). Returns PageOut.
 */
export const POST = withRoute(async (req, ctx) => {
  const { bookId } = await ctx.params;
  require24(bookId, "bookId");

  await verifyAdminToken(req);
  const body = await parseBody(req, PageBaseSchema);

  await db();
  const page = await addPage({
    bookId,
    chapterId: body.chapterId,
    textContent: body.textContent,
    status: body.status,
  });

  await invalidateSummaries({
    books: [bookId],
    pages: [page.id],
    chapters: [page.chapterId],
  });

  return page;
});
