export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { require24 } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { deleteBundle } from "@/lib/payments";

/**
 * DELETE /api/v2/payment/delete-payment-bundle/{bundleId} — admin.
 * Port of `delete_payment_bundle_route` (inherited): `bundleId` must be exactly
 * 24 chars (else 400); returns `{ message: <bool> }` where the bool is whether a
 * document was actually deleted (legacy `JSONResponse({"message": deleted})`).
 */
export const DELETE = withRoute(async (req, ctx) => {
  await verifyAdminToken(req);
  const { bundleId } = await ctx.params;
  require24(bundleId, "bundleId");
  const deleted = await deleteBundle(bundleId);
  return { message: deleted };
});
