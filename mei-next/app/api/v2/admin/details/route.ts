export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { getAdminDetails } from "@/lib/services/admin";

/**
 * GET /api/v2/admin/details  (admin)
 * Returns the calling admin's NewAdminOut (404 "Details not found" if missing).
 * Legacy used response_model_exclude_none — accessToken/refreshToken are null
 * here (no tokens are issued on a read), which keeps the wire shape intact.
 */
export const GET = withRoute(async (req) => {
  const claims = await verifyAdminToken(req);
  return getAdminDetails(claims.accessToken);
});
