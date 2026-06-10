export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { verifyAnyToken } from "@/lib/http/guards";
import { getChapterByNumber } from "@/lib/services/chapter";

/**
 * GET /api/v2/chapter/user/get/{bookId}/{chapterNumber} — member OR admin.
 *
 * `chapterNumber` is an int path param (FastAPI `:int`); a non-integer yields a
 * 422 validation error. Returns `ChapterOut` (404 when missing).
 */
export const GET = withRoute(async (req, ctx) => {
  await verifyAnyToken(req);
  const { bookId, chapterNumber } = await ctx.params;
  if (!/^-?\d+$/.test(chapterNumber)) {
    throw new HttpError(422, "Validation failed", [
      {
        type: "int_parsing",
        loc: ["path", "chapterNumber"],
        msg: "Input should be a valid integer, unable to parse string as an integer",
        input: chapterNumber,
      },
    ]);
  }
  return getChapterByNumber(bookId, parseInt(chapterNumber, 10));
});
