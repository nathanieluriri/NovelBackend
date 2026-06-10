export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { updateAdmin } from "@/lib/services/admin";

/**
 * PATCH /api/v2/admin/update  (admin)
 * Body: AdminUpdate {firstName?, lastName?, avatar?}. Applies the provided keys
 * to the calling admin and returns the refreshed NewAdminOut.
 */
const AdminUpdateSchema = z.object({
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  avatar: z.string().optional(),
});

export const PATCH = withRoute(async (req) => {
  const claims = await verifyAdminToken(req);
  const body = await parseBody(req, AdminUpdateSchema);
  return updateAdmin(claims.accessToken, body);
});
