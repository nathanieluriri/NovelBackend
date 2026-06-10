export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { invalidateSummaries } from "@/lib/cache/summary";
import { toBookOut } from "@/lib/serializers";
import { deleteBook } from "@/lib/services/book";

/**
 * DELETE /api/v2/book/delete/{bookId} — admin-guarded.
 * Cascades to the book's chapters + their pages and reorders remaining books
 * (in the service). Returns the deleted BookOut and busts its summary cache
 * (legacy bust args: `bookId` path + response `id`).
 */
export const DELETE = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { bookId } = await ctx.params;
  const deleted = await deleteBook(bookId);
  const out = toBookOut(deleted);
  await invalidateSummaries({ books: [bookId, out.id] });
  return out;
});
