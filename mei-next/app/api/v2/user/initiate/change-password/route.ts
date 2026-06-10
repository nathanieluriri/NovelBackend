export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { changeOfUserPasswordFlow1 } from "@/lib/services/user";

/**
 * POST /api/v2/user/initiate/change-password  (none) — body {email}.
 * Port of `initiate_change_of_user_password_process` +
 * `change_of_user_password_flow1`: 404 if the user is unknown; else generate +
 * store a user OTP and email it. Returns {message:"Success"}.
 */
const InitiateSchema = z.object({
  email: z.string(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, InitiateSchema);
  await changeOfUserPasswordFlow1(body.email);
  return { message: "Success" };
});
