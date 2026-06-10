export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { after } from "next/server";
import { withRoute } from "@/lib/http/route";
import { require24 } from "@/lib/http/validate";
import { verifyAnyToken, resolveReader } from "@/lib/http/guards";
import { db } from "@/lib/db";
import { fetchSinglePageByPageId, fetchSinglePageByPageIdForUser } from "@/lib/services/page";
import { trackReadingProgress } from "@/lib/services/readingProgress";

/**
 * GET /api/v2/page/get/page/{pageId} — fetch one page.
 * Auth: any. Admins get the raw page (no tracking). Members are access-gated
 * (403) and, on success, schedule a reading-progress upsert via after() so it
 * runs after the response flushes (replaces the legacy FastAPI BackgroundTask;
 * see reading-progress.md). Returns PageOut.
 */
export const GET = withRoute(async (req, ctx) => {
  const { pageId } = await ctx.params;
  require24(pageId, "pageId");

  const claims = await verifyAnyToken(req);
  await db();
  const { role, user } = await resolveReader(claims);

  if (role === "admin") {
    return fetchSinglePageByPageId(pageId);
  }

  const { pageOut, chapterId } = await fetchSinglePageByPageIdForUser(pageId, user!);

  // Members only; admins skip. Guard mirrors legacy: skip if any id is falsy.
  const userId = String(user?._id ?? user?.userId ?? "");
  if (userId && chapterId) {
    after(() => trackReadingProgress(userId, chapterId, pageId));
  }

  return pageOut;
});
