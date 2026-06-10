export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { registerUser } from "@/lib/services/user";

/**
 * POST /api/v2/user/sign-up  (none) — NewUserBase -> NewUserOut.
 * Port of legacy `register` route (api/v1/user.py) + `register_user`.
 * Google provider on the signup body is rejected with 400 (use OAuth);
 * credentials require a password; authProviders normalized; unlockedChapters
 * seeded with the chapter-number-1 id.
 */
const SignUpSchema = z.object({
  provider: z.enum(["credentials", "google"]),
  email: z.string().email(),
  password: z.string().nullish(),
  googleAccessToken: z.string().nullish(),
  firstName: z.string().nullish(),
  lastName: z.string().nullish(),
  avatar: z.string().nullish(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, SignUpSchema);
  return registerUser({
    provider: body.provider,
    email: body.email,
    password: body.password ?? null,
    googleAccessToken: body.googleAccessToken ?? null,
    firstName: body.firstName ?? null,
    lastName: body.lastName ?? null,
    avatar: body.avatar ?? null,
  });
});
