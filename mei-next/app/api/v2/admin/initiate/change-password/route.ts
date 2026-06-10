export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { initiateAdminPasswordChange } from "@/lib/services/admin";

/**
 * POST /api/v2/admin/initiate/change-password  (public)
 * Body: {email}. 404 "Admin Doesn't exist" if no admin; else store + email the
 * password-reset OTP (layout key=otp, value=email). Returns {message:"Success"}.
 */
const EmailBodySchema = z.object({
  email: z.string().email(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, EmailBodySchema);
  await initiateAdminPasswordChange(body.email);
  return { message: "Success" };
});
