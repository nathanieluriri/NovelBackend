export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { parseSkipLimit, paginate } from "@/lib/http/envelope";
import { verifyAnyToken } from "@/lib/http/guards";
import { countBundles, listBundles } from "@/lib/payments";

/**
 * GET /api/v2/payment/get-payment-bundles — any token.
 * Native v2 `get_payment_bundles_v2` (api/v2/payment.py): paginated bundle list.
 * Response data: PaginatedListOut[PaymentBundlesOut].
 *
 * `listBundles` already maps docs through `toPaymentBundlesOut`, so items are
 * wire shapes; `skip < 0` → 400 and `limit` clamping are handled by parseSkipLimit.
 */
export const GET = withRoute(async (req) => {
  await verifyAnyToken(req);
  const { skip, limit } = parseSkipLimit(req);
  const [items, total] = await Promise.all([listBundles(skip, limit), countBundles()]);
  return paginate(items, skip, limit, total);
});
