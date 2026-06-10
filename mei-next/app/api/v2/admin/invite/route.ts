export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAdminToken } from "@/lib/http/guards";
import { processInvitation } from "@/lib/services/admin";

/**
 * POST /api/v2/admin/invite  (admin)
 * Body: {email}. Resolve the inviter from the active admin token; if the
 * inviter's firstName != "Default" write an AllowedAdmin allowlist row; then
 * email the invitation (best-effort). Returns {message:"success"}.
 */
const InviteSchema = z.object({
  email: z.string().email(),
});

export const POST = withRoute(async (req) => {
  const claims = await verifyAdminToken(req);
  const body = await parseBody(req, InviteSchema);
  await processInvitation(claims.accessToken, body.email);
  return { message: "success" };
});
