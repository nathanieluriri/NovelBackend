export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAnyToken } from "@/lib/http/guards";
import { getChapterById } from "@/lib/services/chapter";

/**
 * GET /api/v2/chapter/user/get/chapterId/{chapterId} — member OR admin.
 * Returns `ChapterOut` (404 when missing).
 */
export const GET = withRoute(async (req, ctx) => {
  await verifyAnyToken(req);
  const { chapterId } = await ctx.params;
  return getChapterById(chapterId);
});
