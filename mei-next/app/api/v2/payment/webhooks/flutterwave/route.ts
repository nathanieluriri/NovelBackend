export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { processWebhook } from "@/lib/payments";

/**
 * POST /api/v2/payment/webhooks/flutterwave — public (signature only).
 * Port of `flutterwave_webhook` (inherited). Read the RAW body (never `req.json()`,
 * or `verif-hash` verification breaks); pass lowercased headers (Headers entries
 * are already lowercase) to the orchestrator.
 */
export const POST = withRoute(async (req) => {
  const raw = await req.text();
  const headers: Record<string, string> = {};
  for (const [key, value] of req.headers.entries()) headers[key] = value;
  return processWebhook("flutterwave", raw, headers);
});
