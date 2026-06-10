export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody, require24 } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { updateBundle, type PaymentBundleUpdateInput, type BundleType } from "@/lib/payments";

/**
 * PaymentBundlesUpdate — all optional (schema.md §5). Non-negative / per-type
 * checks and the "subscription"→"subscriptionCash" normalization run inside
 * `updateBundle`.
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

const PaymentBundlesUpdate = z.object({
  amount: z.number().int().nullish(),
  bundleType: z.enum(BUNDLE_TYPES).nullish(),
  numberOfstars: z.number().int().nullish(),
  durationDays: z.number().int().nullish(),
  description: z.string().nullish(),
});

/**
 * PATCH /api/v2/payment/update-payment-bundle/{bundleId} — admin.
 * Port of `update_payment_bundle_route` (inherited): `bundleId` must be exactly
 * 24 chars (else 400); returns `{ message: <bool> }` where the bool is whether a
 * document was actually modified (legacy `JSONResponse({"message": updated})`).
 */
export const PATCH = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { bundleId } = await ctx.params;
  require24(bundleId, "bundleId");
  const body = await parseBody(req, PaymentBundlesUpdate);
  const updated = await updateBundle(bundleId, body as PaymentBundleUpdateInput);
  return { message: updated };
});
