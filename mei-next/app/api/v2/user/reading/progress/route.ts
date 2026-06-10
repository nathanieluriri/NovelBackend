export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { withRoute } from "@/lib/http/route";
import { HttpError } from "@/lib/http/errors";
import { verifyToken } from "@/lib/http/guards";
import { getUserReadingProgress } from "@/lib/services/readingProgress";
import { excludeNone, getUserDetailsWithAccessToken } from "@/lib/services/user";

/**
 * GET /api/v2/user/reading/progress  (member) — ReadingProgressOut.
 * Port of `get_stopped_reading_progress_v2` (api/v2/user.py): resolve the user
 * (401 if absent), then `getUserReadingProgress` which raises 404/403 when
 * inaccessible (propagated here, unlike /user/details which swallows them).
 * Legacy used `response_model_exclude_none=True` — null keys dropped.
 */
export const GET = withRoute(async (req) => {
  const claims = await verifyToken(req);
  const user = await getUserDetailsWithAccessToken(claims.accessToken);
  if (!user) throw new HttpError(401, "Invalid token");

  const progress = await getUserReadingProgress(user.userId);
  return excludeNone(progress);
});
