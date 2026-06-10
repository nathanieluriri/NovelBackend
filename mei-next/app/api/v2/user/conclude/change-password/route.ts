export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { changeOfUserPasswordFlow2 } from "@/lib/services/user";

/**
 * POST /api/v2/user/conclude/change-password  (none) — body {email,otp,password}.
 * Port of `conclude_change_of_user_password_process` +
 * `change_of_user_password_flow2`: verify OTP -> hash -> replace password ->
 * revoke all tokens for the user. Legacy returns `{"message": result}` where
 * `result` is the raw boolean (true on success, false on bad OTP) — preserved.
 */
const ConcludeSchema = z.object({
  email: z.string(),
  otp: z.string(),
  password: z.string(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, ConcludeSchema);
  const result = await changeOfUserPasswordFlow2(body.email, body.otp, body.password);
  return { message: result };
});
