export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAnyToken } from "@/lib/http/guards";
import { getPricingCatalog } from "@/lib/payments";

/**
 * GET /api/v2/payment/pricing — any token.
 * Port of `get_pricing_catalog_route` (api/v1/payment.py, inherited by v2).
 * Response data: PricingCatalogOut (subscriptionPlans / starBundles /
 * chapterUnlockBundles, each grouped from the bundle catalog).
 */
export const GET = withRoute(async (req) => {
  await verifyAnyToken(req);
  return getPricingCatalog();
});
