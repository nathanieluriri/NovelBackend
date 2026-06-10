export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { buildGoogleAuthRedirect } from "@/lib/auth";

/**
 * GET /api/v2/user/google/auth — start the Google OAuth flow.
 * Port of `login_with_google` (../api/v1/user.py) → `start_google_oauth`.
 *
 * Query:
 *  - `target`        optional frontend alias (must resolve in
 *                    GOOGLE_OAUTH_REDIRECT_TARGETS; unknown alias → 400).
 *  - `redirect_path` optional relative post-login path; the legacy FastAPI
 *                    `Query(max_length=512)` rejects anything longer with a 422.
 *
 * Returns the raw 302 redirect to Google (withRoute passes Responses through).
 */
const MAX_REDIRECT_PATH_LENGTH = 512;

export const GET = withRoute(async (req) => {
  const sp = new URL(req.url).searchParams;
  const target = sp.get("target") ?? undefined;
  const redirectPath = sp.get("redirect_path");

  if (redirectPath !== null && redirectPath.length > MAX_REDIRECT_PATH_LENGTH) {
    throw new HttpError(422, "Validation failed", [
      {
        type: "string_too_long",
        loc: ["query", "redirect_path"],
        msg: `String should have at most ${MAX_REDIRECT_PATH_LENGTH} characters`,
        input: redirectPath,
      },
    ]);
  }

  return buildGoogleAuthRedirect(target, redirectPath ?? undefined);
});
