export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { verifyAdminToken } from "@/lib/http/guards";
import { getAllAdminDetails } from "@/lib/services/admin";

/**
 * GET /api/v2/admin/all/details  (admin)
 * Returns every admin as a list of NewAdminOut.
 */
export const GET = withRoute(async (req) => {
  await verifyAdminToken(req);
  return getAllAdminDetails();
});
