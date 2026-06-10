export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { invalidateSummaries } from "@/lib/cache/summary";
import { toBookOut } from "@/lib/serializers";
import { createBook } from "@/lib/services/book";

/** BookBaseRequest — `{ name }`, no extra validators (schema.md §5). */
const BookBaseRequest = z.object({ name: z.string() });

/**
 * POST /api/v2/book/create — admin-guarded book creation.
 * Body: BookBaseRequest → BookOut. Busts the new book's summary cache.
 */
export const POST = withRoute(async (req) => {
  await verifyAdminToken(req);
  const body = await parseBody(req, BookBaseRequest);
  const created = await createBook(body.name);
  const out = toBookOut(created);
  await invalidateSummaries({ books: [out.id] });
  return out;
});
