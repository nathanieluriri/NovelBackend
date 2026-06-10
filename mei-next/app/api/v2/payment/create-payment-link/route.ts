export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyToken, getUserFromClaims } from "@/lib/http/guards";
import { createCheckout, type CheckoutCreateRequest } from "@/lib/payments";

/** PaymentLink — `{ bundle_id }` (schema.md §5). */
const PaymentLink = z.object({ bundle_id: z.string() });

/**
 * POST /api/v2/payment/create-payment-link — member, compatibility wrapper.
 * Port of `create_payment_link` (inherited): forces NG / flutterwave, builds a
 * CheckoutCreateRequest from `bundle_id`, runs `createCheckout`, then reshapes the
 * session into the legacy `{ link, tx_ref, provider }` payload.
 */
export const POST = withRoute(async (req) => {
  const claims = await verifyToken(req);
  const { bundle_id } = await parseBody(req, PaymentLink);
  const user = await getUserFromClaims(claims);

  const checkoutRequest: CheckoutCreateRequest = {
    bundleId: bundle_id,
    countryCode: "NG",
    provider: "flutterwave",
  };
  const session = await createCheckout(user, checkoutRequest);

  return {
    link: session.checkoutUrl,
    tx_ref: session.txRef,
    provider: session.provider,
  };
});
