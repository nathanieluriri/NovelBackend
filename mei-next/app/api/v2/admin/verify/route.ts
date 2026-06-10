export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyAdminOtp } from "@/lib/services/admin";

/**
 * POST /api/v2/admin/verify  (public)
 * Body: VerificationRequest {access_token, otp}. Verifies the admin login OTP
 * (Redis key=adminJWT, value=otp), then flips the admin access-token row to
 * `status:"active"`. Returns `{message: true}` on success; 401 "Incorrect OTP"
 * on mismatch/expiry.
 */
const VerificationRequestSchema = z.object({
  access_token: z.string(),
  otp: z.string(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, VerificationRequestSchema);
  const result = await verifyAdminOtp(body.access_token, body.otp);
  return { message: result };
});
