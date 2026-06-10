export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { createBundle, type PaymentBundleCreateInput, type BundleType } from "@/lib/payments";

/**
 * PaymentBundles (admin create) — schema.md §5. Shape only here; the per-type
 * rules (subscriptionCash⇒amount+duration, subscriptionStars⇒stars+duration,
 * cash/purchaseOfBooks⇒stars>0, non-negative checks, "subscription"→
 * "subscriptionCash") live in `createBundle` and fire as 422 there.
 */
const BUNDLE_TYPES = [
  "cash",
  "purchaseOfBooks",
  "transferringStarsToOtherUsers",
  "cashPromo",
  "bookPromo",
  "subscription",
  "subscriptionCash",
  "subscriptionStars",
] as const satisfies readonly BundleType[];

const PaymentBundles = z.object({
  bundleType: z.enum(BUNDLE_TYPES),
  amount: z.number().int().nullish(),
  numberOfstars: z.number().int().nullish(),
  durationDays: z.number().int().nullish(),
  description: z.string(),
});

/**
 * POST /api/v2/payment/create-payment-bundle — admin.
 * Port of `create_payment_bundle_route` (inherited). Body: PaymentBundles →
 * PaymentBundlesOut.
 */
export const POST = withRoute(async (req) => {
  await verifyAdminToken(req);
  const body = await parseBody(req, PaymentBundles);
  return createBundle(body as PaymentBundleCreateInput);
});
