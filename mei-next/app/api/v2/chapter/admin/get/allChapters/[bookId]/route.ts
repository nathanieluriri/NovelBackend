export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAdminToken } from "@/lib/http/guards";
import { listChapters, countChapters } from "@/lib/services/chapter";

/**
 * GET /api/v2/chapter/admin/get/allChapters/{bookId} — admin.
 * `skip=0,limit=20`. Returns `PaginatedListOut[ChapterOut]`.
 */
export const GET = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { bookId } = await ctx.params;
  const { skip, limit } = parseSkipLimit(req);

  const [items, total] = await Promise.all([
    listChapters(bookId, skip, limit),
    countChapters(bookId),
  ]);
  return paginate(items, skip, limit, total);
});
