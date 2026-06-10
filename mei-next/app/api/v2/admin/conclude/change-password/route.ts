export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { concludeAdminPasswordChange } from "@/lib/services/admin";

/**
 * POST /api/v2/admin/conclude/change-password  (public)
 * Body: {email, otp, password}. Verify the reset OTP; on success bcrypt + store
 * the new password and revoke all tokens (logout everywhere). Returns
 * {message: true|false} (legacy returned the boolean verbatim).
 */
const ConcludeSchema = z.object({
  email: z.string().email(),
  otp: z.string(),
  password: z.string(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, ConcludeSchema);
  const result = await concludeAdminPasswordChange(body.email, body.otp, body.password);
  return { message: result };
});
