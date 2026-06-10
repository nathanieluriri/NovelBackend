export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { processWebhook } from "@/lib/payments";

/**
 * POST /api/v2/payment/webhooks/stripe — public (signature only).
 * Port of `stripe_webhook` (inherited). Read the RAW body (Stripe
 * `Webhook.constructEvent` needs the exact bytes for `stripe-signature`); pass
 * lowercased headers (Headers entries are already lowercase) to the orchestrator.
 */
export const POST = withRoute(async (req) => {
  const raw = await req.text();
  const headers: Record<string, string> = {};
  for (const [key, value] of req.headers.entries()) headers[key] = value;
  return processWebhook("stripe", raw, headers);
});
