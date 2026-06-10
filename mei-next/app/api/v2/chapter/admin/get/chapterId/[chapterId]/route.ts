export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { getChapterById } from "@/lib/services/chapter";

/**
 * GET /api/v2/chapter/admin/get/chapterId/{chapterId} — admin.
 * Returns `ChapterOut` (404 when missing).
 */
export const GET = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { chapterId } = await ctx.params;
  return getChapterById(chapterId);
});
