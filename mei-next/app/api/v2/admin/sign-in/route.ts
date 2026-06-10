export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { loginAdmin } from "@/lib/services/admin";

/**
 * POST /api/v2/admin/sign-in  (public)
 * Body: AdminBase {email, password}. Same OTP / inactive-token flow as sign-up:
 * verify the password, issue inactive admin tokens, store + email the login OTP
 * (+ IP-change warning per legacy). Returns NewAdminOut.
 */
const AdminBaseSchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, AdminBaseSchema);
  return loginAdmin(req, { email: body.email, password: body.password });
});
