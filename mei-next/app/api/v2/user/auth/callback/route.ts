export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { handleGoogleCallback } from "@/lib/auth";

/**
 * GET /api/v2/user/auth/callback — alias of /api/v2/user/google/callback.
 * The legacy router mounts both paths on the same `google_auth_callback`
 * handler (../api/v1/user.py). Same behavior, same handler.
 */
export const GET = withRoute(async (req) => handleGoogleCallback(req));
