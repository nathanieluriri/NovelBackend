export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { excludeNone, loginCredentials } from "@/lib/services/user";

/**
 * POST /api/v2/user/sign-in  (none) — OldUserBase -> OldUserOut.
 * Port of legacy `login` route + `login_credentials` +
 * `build_authenticated_user_output`. Google provider on the body is rejected
 * with 400; bcrypt verified; member tokens issued; bookmarks + likes hydrated.
 * Legacy route used `response_model_exclude_none=True` — null keys dropped.
 */
const SignInSchema = z.object({
  provider: z.enum(["credentials", "google"]),
  email: z.string().email(),
  password: z.string().nullish(),
  googleAccessToken: z.string().nullish(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, SignInSchema);
  const user = await loginCredentials({
    provider: body.provider,
    email: body.email,
    password: body.password ?? null,
    googleAccessToken: body.googleAccessToken ?? null,
  });
  return excludeNone(user);
});
