export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { getChapterByNumber } from "@/lib/services/chapter";

/**
 * GET /api/v2/chapter/admin/get/{bookId}/{chapterNumber} — PUBLIC.
 *
 * ⚠ Legacy quirk preserved: this "admin" path carries NO auth dependency in the
 * legacy router (unlike its siblings). Keep it public — do not add a guard.
 *
 * `chapterNumber` is an int path param (FastAPI `:int`); a non-integer yields a
 * 422 validation error. Returns `ChapterOut` (404 when missing).
 */
export const GET = withRoute(async (req, ctx) => {
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
