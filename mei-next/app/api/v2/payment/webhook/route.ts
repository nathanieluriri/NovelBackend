export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { processWebhook } from "@/lib/payments";

/**
 * POST /api/v2/payment/webhook — public legacy compatibility alias for flutterwave.
 * Port of `legacy_flutterwave_webhook` (inherited): same handler as
 * `/webhooks/flutterwave` for provider dashboards that can't be reconfigured.
 * Read the RAW body; pass lowercased headers (Headers entries are already lowercase).
 */
export const POST = withRoute(async (req) => {
  const raw = await req.text();
  const headers: Record<string, string> = {};
  for (const [key, value] of req.headers.entries()) headers[key] = value;
  return processWebhook("flutterwave", raw, headers);
});
