export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { registerAdmin } from "@/lib/services/admin";

/**
 * POST /api/v2/admin/sign-up  (public)
 * Body: NewAdminCreate. Allowlist-gated (400 if not allowed, 409 if exists).
 * bcrypt the password; issue ADMIN tokens (the access row is inactive); store +
 * email the admin login OTP (+ IP-change warning per legacy). Returns NewAdminOut
 * with the (still-inactive) tokens.
 */
const NewAdminCreateSchema = z.object({
  email: z.string().email(),
  password: z.string(),
  // Legacy `Optional[str]` with no default = required-but-nullable (Pydantic v2).
  firstName: z.string().nullable(),
  lastName: z.string().nullable(),
  // Legacy `Optional[str] = None` = truly optional.
  avatar: z.string().nullish(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, NewAdminCreateSchema);
  return registerAdmin(req, {
    email: body.email,
    password: body.password,
    firstName: body.firstName,
    lastName: body.lastName,
    avatar: body.avatar ?? null,
  });
});
