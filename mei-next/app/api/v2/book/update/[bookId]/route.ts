export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { invalidateSummaries } from "@/lib/cache/summary";
import { toBookOut } from "@/lib/serializers";
import { updateBook } from "@/lib/services/book";

/**
 * BookUpdate — all optional (schema.md §5). `dateUpdated` is auto-stamped by the
 * service (legacy `set_dates` validator), so it is not accepted from the body.
 * `chapterCount` defaults to 0 and is always persisted (legacy `exclude_none`
 * keeps it because its default is 0, not None).
 */
const BookUpdate = z.object({
  name: z.string().nullish(),
  number: z.number().nullish(),
  chapterCount: z.number().nullish(),
  chapters: z.array(z.string()).nullish(),
});

/**
 * PATCH /api/v2/book/update/{bookId} — admin-guarded.
 * Body: BookUpdate → BookOut. Busts the updated book's summary cache
 * (legacy bust args: `bookId` path + response `id`).
 */
export const PATCH = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { bookId } = await ctx.params;
  const body = await parseBody(req, BookUpdate);
  const updated = await updateBook(bookId, body);
  const out = toBookOut(updated);
  await invalidateSummaries({ books: [bookId, out.id] });
  return out;
});
