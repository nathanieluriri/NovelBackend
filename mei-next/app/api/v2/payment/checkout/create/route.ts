export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyToken, getUserFromClaims } from "@/lib/http/guards";
import { createCheckout, type CheckoutCreateRequest } from "@/lib/payments";

/**
 * CheckoutCreateRequest — schema.md §5. The legacy model-validator raises
 * (→ 422) when `bundleId`/`chapterId` are not exactly 24 chars, and uppercases
 * `countryCode` (which is also length-2). NG⇒provider∈{flutterwave,paystack}
 * and non-NG⇒forced stripe are enforced downstream by `resolveProvider`.
 */
const CheckoutCreateRequestSchema = z
  .object({
    bundleId: z.string().length(24, "bundleId must be exactly 24 characters long"),
    countryCode: z.string().length(2).transform((c) => c.toUpperCase()),
    provider: z.enum(["flutterwave", "paystack", "stripe"]).nullish(),
    chapterId: z.string().length(24, "chapterId must be exactly 24 characters long").nullish(),
    successUrl: z.string().nullish(),
    cancelUrl: z.string().nullish(),
  });

/**
 * POST /api/v2/payment/checkout/create — member.
 * Port of `create_checkout_route` (inherited): resolve the member user from the
 * access token, then run the cash-checkout orchestrator. Returns CheckoutSessionOut
 * (enveloped by withRoute — v2 parity).
 */
export const POST = withRoute(async (req) => {
  const claims = await verifyToken(req);
  const body = await parseBody(req, CheckoutCreateRequestSchema);
  const user = await getUserFromClaims(claims);
  return createCheckout(user, body as CheckoutCreateRequest);
});
