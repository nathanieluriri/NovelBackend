export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { require24 } from "@/lib/http/validate";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAnyToken, resolveReader } from "@/lib/http/guards";
import { db } from "@/lib/db";
import { fetchPages, fetchPagesForUser, fetchPagesCount } from "@/lib/services/page";

/**
 * GET /api/v2/page/get/{chapterId} — list pages in a chapter.
 * Auth: any (member OR admin). Admin sees all; member is access-gated (403).
 * Returns PaginatedListOut[PageOut].
 */
export const GET = withRoute(async (req, ctx) => {
  const { chapterId } = await ctx.params;
  require24(chapterId, "chapterId");
  const claims = await verifyAnyToken(req);
  const { skip, limit } = parseSkipLimit(req);
  await db();
  const { role, user } = await resolveReader(claims);

  const items =
    role === "admin"
      ? await fetchPages(chapterId, skip, limit)
      : await fetchPagesForUser(chapterId, user!, skip, limit);

  const total = await fetchPagesCount(chapterId);
  return paginate(items, skip, limit, total);
});
