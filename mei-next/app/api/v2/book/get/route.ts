export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAdminToken } from "@/lib/http/guards";
import { toBookOut } from "@/lib/serializers";
import { listBooks, countBooks } from "@/lib/services/book";

/**
 * GET /api/v2/book/get — admin-guarded paginated book list.
 * (Legacy v2 `get_books_v2`; the book router carries a router-level admin dep.)
 * Response data: PaginatedListOut[BookOut].
 */
export const GET = withRoute(async (req) => {
  await verifyAdminToken(req);
  const { skip, limit } = parseSkipLimit(req);
  const [books, total] = await Promise.all([listBooks(skip, limit), countBooks()]);
  return paginate(books.map(toBookOut), skip, limit, total);
});
