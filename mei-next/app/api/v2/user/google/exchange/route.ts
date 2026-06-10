export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { z } from "zod";
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { withRoute } from "@/lib/http/route";
import { parseBody } from "@/lib/http/validate";
import { exchangeGoogleCode, issueMemberTokens } from "@/lib/auth";
import { getChapterSummary } from "@/lib/cache/summary";
import { Bookmark, Like, User, type UserDoc } from "@/lib/models";
import {
  toBookmarkOut,
  toLikeOut,
  toOldUserOut,
  type BookMarkOut,
  type LikeOut,
  type OldUserOut,
} from "@/lib/serializers";

/**
 * POST /api/v2/user/google/exchange — exchange the one-time OAuth code for a
 * member session. Port of `exchange_google_login` (../api/v1/user.py) →
 * `exchange_google_oauth_code` → `build_authenticated_user_output`
 * (../services/user_service.py). sequence.md diagram 4.
 *
 * Flow (exact legacy error codes/messages):
 *  1. validate body `{code}` (min length 1, stripped).
 *  2. `exchangeGoogleCode` atomically consumes the code; invalid/expired/used
 *     → 401 "Google OAuth code is invalid, expired, or already used".
 *  3. load the user → 404 "User not found".
 *  4. issue member tokens (same as sign-in).
 *  5. hydrate bookmarks + likes (chapterSummary-enriched, like the legacy
 *     `retrieve_user_bookmark` / `retrieve_user_likes`) and return `OldUserOut`.
 */

const ExchangeBody = z.object({ code: z.string().min(1) });

/** Mirrors `retrieve_user_bookmark`: all of a user's bookmarks, chapterSummary-enriched. */
async function loadUserBookmarks(userId: string): Promise<BookMarkOut[]> {
  const docs = await Bookmark.find({ userId }).lean<Record<string, unknown>[]>();
  const out: BookMarkOut[] = [];
  for (const doc of docs) {
    const bookmark = toBookmarkOut(doc);
    if (bookmark.chapterId) {
      bookmark.chapterSummary = await getChapterSummary(bookmark.chapterId);
    }
    out.push(bookmark);
  }
  return out;
}

/** Mirrors `retrieve_user_likes`: all of a user's likes, chapterSummary-enriched. */
async function loadUserLikes(userId: string): Promise<LikeOut[]> {
  const docs = await Like.find({ userId }).lean<Record<string, unknown>[]>();
  const out: LikeOut[] = [];
  for (const doc of docs) {
    const like = toLikeOut(doc);
    if (like.chapterId) {
      like.chapterSummary = await getChapterSummary(like.chapterId);
    }
    out.push(like);
  }
  return out;
}

export const POST = withRoute(async (req): Promise<OldUserOut> => {
  const body = await parseBody(req, ExchangeBody);
  const code = body.code.trim();
  if (!code) {
    throw new HttpError(422, "Validation failed", [
      { type: "value_error", loc: ["body", "code"], msg: "Google OAuth code is required", input: body.code },
    ]);
  }

  const { userId } = await exchangeGoogleCode(code);

  await db();
  const user = await User.findById(userId).lean<UserDoc>();
  if (!user) throw new HttpError(404, "User not found");

  const realUserId = String(user._id);
  const { accessToken, refreshToken } = await issueMemberTokens(realUserId);
  const [bookmarks, likes] = await Promise.all([
    loadUserBookmarks(realUserId),
    loadUserLikes(realUserId),
  ]);

  return toOldUserOut(user, { accessToken, refreshToken, bookmarks, likes });
});
