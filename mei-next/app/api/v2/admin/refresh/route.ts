export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { refreshTokens } from "@/lib/auth";

/**
 * POST /api/v2/admin/refresh  (pair: expired-OK admin access JWT + refresh row)
 * Body: refreshTokenRequest {refreshToken} + Authorization: Bearer <accessJWT>.
 * Full rotation via the admin path (new access row activated immediately, old
 * rows deleted). 404 "Refresh Token is Invalid" when the old refresh row is gone.
 * Returns {userId, dateCreated, refreshToken, accessToken}.
 */
const RefreshTokenRequestSchema = z.object({
  refreshToken: z.string(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, RefreshTokenRequestSchema);
  return refreshTokens(req, body.refreshToken);
});
