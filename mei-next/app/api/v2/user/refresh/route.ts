export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";

import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { refreshTokens } from "@/lib/auth";

/**
 * POST /api/v2/user/refresh  (pair) — body refreshTokenRequest {refreshToken}
 * + the (expired-OK) access JWT in `Authorization: Bearer`.
 * Port of legacy `refresh_access_token` + `verify_token_and_refresh_token`:
 * full rotation (new access row/JWT + new refresh row, old access row deleted),
 * then the old refresh row deleted by body.refreshToken (404 if missing).
 * Returns {userId, dateCreated, refreshToken, accessToken} (all new).
 */
const RefreshSchema = z.object({
  refreshToken: z.string(),
});

export const POST = withRoute(async (req) => {
  const body = await parseBody(req, RefreshSchema);
  return refreshTokens(req, body.refreshToken);
});
