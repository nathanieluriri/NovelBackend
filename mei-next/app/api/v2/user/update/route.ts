export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { verifyToken } from "@/lib/http/guards";
import { excludeNone, updateUser } from "@/lib/services/user";

/**
 * PATCH /api/v2/user/update  (member) — UserUpdate -> NewUserOut.
 * Port of `update` route + `update_user`: apply the non-null fields, then
 * re-read the user. Legacy used `response_model_exclude_none=True` — null keys
 * dropped from the response.
 */
const UserUpdateSchema = z.object({
  firstName: z.string().nullish(),
  lastName: z.string().nullish(),
  avatar: z.string().nullish(),
  status: z.enum(["Active", "Inactive", "Suspended"]).nullish(),
});

export const PATCH = withRoute(async (req) => {
  const body = await parseBody(req, UserUpdateSchema);
  const claims = await verifyToken(req);
  const user = await updateUser(claims.accessToken, {
    firstName: body.firstName ?? null,
    lastName: body.lastName ?? null,
    avatar: body.avatar ?? null,
    status: body.status ?? null,
  });
  return excludeNone(user);
});
