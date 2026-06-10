export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { handleGoogleCallback } from "@/lib/auth";

/**
 * GET /api/v2/user/google/callback — Google redirects here with `code`/`state`.
 * Port of `google_auth_callback` (../api/v1/user.py) → `handle_google_oauth_callback`.
 * Exchanges the code, upserts the user, mints a one-time exchange code, and
 * 302s the browser back to the frontend success/error URL (raw Response).
 */
export const GET = withRoute(async (req) => handleGoogleCallback(req));
