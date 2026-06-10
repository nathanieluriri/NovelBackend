/**
 * User core service — port of `../app/services/user_service.py`
 * (+ the v1/v2 user routers' inline logic) for the v2 user surface.
 *
 * Responsibilities (see auth.md, sequence.md §1/§3, schema.md §4/§5):
 *  - register (sign-up): credentials-only password, authProviders normalize,
 *    seed unlockedChapters with chapter-number-1's id, bcrypt hash, 409 on dup.
 *  - login (sign-in): lookup by email + credentials provider, bcrypt verify,
 *    issue member tokens, hydrate bookmarks + likes (build_authenticated_user_output).
 *  - get user-with-token: session row -> user, hydrated with bookmarks + likes.
 *  - password reset flows (initiate / conclude).
 *  - profile update.
 *  - likes/bookmarks retrieval + counts (for the v2 aggregate + list routes).
 *
 * Models are imported DIRECTLY (CONVENTIONS.md: this slice may touch Like /
 * Bookmark / User / Chapter models; it must NOT import other domain services).
 */
import { Types } from "mongoose";

import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { nowIso } from "@/lib/util/dates";
import { hashPassword, checkPassword } from "@/lib/auth/hash";
import {
  issueMemberTokens,
  generateOtp,
  storeUserOtp,
  verifyUserOtp,
  revokeAllTokensForUser,
  getAccessTokenRow,
} from "@/lib/auth";
import { sendPasswordResetOtp } from "@/lib/email";
import { getChapterSummary } from "@/lib/cache/summary";
import {
  Bookmark,
  Chapter,
  Like,
  User,
  type BookmarkDoc,
  type LikeDoc,
  type UserDoc,
} from "@/lib/models";
import {
  toBookmarkOut,
  toLikeOut,
  toNewUserOut,
  toOldUserOut,
  toUserOut,
  type BookMarkOutAsync,
  type LikeOut,
  type NewUserOut,
  type OldUserOut,
  type UserOut,
} from "@/lib/serializers";

/* eslint-disable @typescript-eslint/no-explicit-any */
type AnyDoc = Record<string, any>;

/**
 * Recursively drop null/undefined-valued keys — mirrors FastAPI
 * `response_model_exclude_none=True` (used by sign-in, /reading/progress,
 * /update, and the inherited details route). Arrays are walked element-wise;
 * plain objects are rebuilt without their null keys. Leaves non-plain values
 * (e.g. Date) untouched.
 */
export function excludeNone<T>(value: T): T {
  if (value === null || value === undefined) return value;
  if (Array.isArray(value)) {
    return value.map((v) => excludeNone(v)) as unknown as T;
  }
  if (typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (v === null || v === undefined) continue;
      out[k] = excludeNone(v);
    }
    return out as unknown as T;
  }
  return value;
}

// ---------------------------------------------------------------------------
// authProviders normalization — port of `_normalize_auth_providers`
// (schemas/user_schema.py): lowercase, trim, dedupe; the create-time `provider`
// is appended last if not already present.
// ---------------------------------------------------------------------------
function normalizeAuthProviders(authProviders: unknown, provider: unknown): string[] {
  const out: string[] = [];
  const push = (v: unknown) => {
    if (typeof v !== "string") return;
    const candidate = v.trim().toLowerCase();
    if (candidate && !out.includes(candidate)) out.push(candidate);
  };
  if (Array.isArray(authProviders)) for (const item of authProviders) push(item);
  push(provider);
  return out;
}

// ---------------------------------------------------------------------------
// unlockedChapters seeding — port of `get_chapter_one_id` + the async field
// validator `set_default_chapter` (schemas/user_schema.py). The default user is
// seeded with the id of the chapter whose `number == 1`, IF one exists.
// Legacy raised on a missing chapter; here it is swallowed so signup still works.
// ---------------------------------------------------------------------------
async function getChapterOneId(): Promise<string | null> {
  const chapter = await Chapter.findOne({ number: 1 }, { _id: 1 }).lean<AnyDoc>();
  if (!chapter || chapter._id === null || chapter._id === undefined) return null;
  return String(chapter._id);
}

async function seedUnlockedChapters(initial: string[]): Promise<string[]> {
  const seeded = [...initial];
  try {
    const chapterOneId = await getChapterOneId();
    if (chapterOneId && !seeded.includes(chapterOneId)) seeded.push(chapterOneId);
  } catch {
    // legacy would raise; keep signup resilient if no chapter-1 exists
  }
  return seeded;
}

// ---------------------------------------------------------------------------
// Activity hydration — `_load_user_activity` in user_service.py:
// asyncio.gather(retrieve_user_bookmark(userId), retrieve_user_likes(userId)).
// Legacy defaults: bookmarks limit=20, likes limit=None (all). chapterSummary
// hydrated per-item from the summary cache when chapterId is present.
// ---------------------------------------------------------------------------
async function loadUserActivity(
  userId: string,
): Promise<{ bookmarks: BookMarkOutAsync[]; likes: LikeOut[] }> {
  const [bookmarks, likes] = await Promise.all([
    retrieveUserBookmarks(userId, 0, 20),
    retrieveUserLikes(userId, 0, null),
  ]);
  return { bookmarks, likes };
}

/** Issue member tokens (access JWT + refresh id). */
async function issueTokens(userId: string): Promise<{ accessToken: string; refreshToken: string }> {
  return issueMemberTokens(userId);
}

// ---------------------------------------------------------------------------
// Likes / Bookmarks retrieval + counts (ports of like_services /
// bookmark_services retrieval helpers + their repos). Used by the v2 aggregate
// and the /user/likes /user/bookmarks list routes.
// ---------------------------------------------------------------------------

/** Port of `retrieve_user_likes`: likes for userId, each hydrated w/ chapterSummary. */
export async function retrieveUserLikes(
  userId: string,
  skip = 0,
  limit: number | null = null,
): Promise<LikeOut[]> {
  await db();
  let q = Like.find({ userId }).skip(skip);
  if (limit !== null) q = q.limit(limit);
  const docs = await q.lean<LikeDoc[]>();
  const out: LikeOut[] = [];
  for (const doc of docs) {
    const chapterId = doc.chapterId ? String(doc.chapterId) : "";
    const summary = chapterId ? await getChapterSummary(chapterId) : null;
    out.push(toLikeOut(doc, summary));
  }
  return out;
}

/** Port of `count_user_likes`. */
export async function retrieveUserLikesCount(userId: string): Promise<number> {
  await db();
  return Like.countDocuments({ userId });
}

/** Port of `retrieve_user_bookmark`: bookmarks for userId, hydrated w/ chapterSummary. */
export async function retrieveUserBookmarks(
  userId: string,
  skip = 0,
  limit = 20,
): Promise<BookMarkOutAsync[]> {
  await db();
  const docs = await Bookmark.find({ userId }).skip(skip).limit(limit).lean<BookmarkDoc[]>();
  const out: BookMarkOutAsync[] = [];
  for (const doc of docs) {
    const chapterId = doc.chapterId ? String(doc.chapterId) : "";
    const summary = chapterId ? await getChapterSummary(chapterId) : null;
    out.push(toBookmarkOut(doc, { chapterSummary: summary }));
  }
  return out;
}

/** Port of `count_user_bookmarks`. */
export async function retrieveUserBookmarksCount(userId: string): Promise<number> {
  await db();
  return Bookmark.countDocuments({ userId });
}

// ---------------------------------------------------------------------------
// Lookups
// ---------------------------------------------------------------------------

async function getUserByEmail(email: string): Promise<UserDoc | null> {
  await db();
  return User.findOne({ email }).lean<UserDoc>();
}

/**
 * Port of `get_user_by_email_and_provider(email, "credentials")`: match email
 * AND (provider === "credentials" OR "credentials" in authProviders).
 */
async function getCredentialsUserByEmail(email: string): Promise<UserDoc | null> {
  await db();
  return User.findOne({
    email,
    $or: [{ provider: "credentials" }, { authProviders: "credentials" }],
  }).lean<UserDoc>();
}

async function getUserById(userId: string): Promise<UserDoc | null> {
  await db();
  if (!Types.ObjectId.isValid(userId)) return null;
  return User.findById(userId).lean<UserDoc>();
}

// ---------------------------------------------------------------------------
// Sign-up — port of `register` route + `register_user` service.
// ---------------------------------------------------------------------------
export interface SignUpInput {
  provider: "credentials" | "google";
  email: string;
  password?: string | null;
  googleAccessToken?: string | null;
  firstName?: string | null;
  lastName?: string | null;
  avatar?: string | null;
}

export async function registerUser(input: SignUpInput): Promise<NewUserOut> {
  await db();

  // Route-level guard: Google provider rejected on signup body (use OAuth).
  if (input.provider === "google") {
    throw new HttpError(
      400,
      "Google OAuth now uses /api/v1/user/google/auth and /api/v1/user/google/exchange",
    );
  }

  // model_validator: credentials require a password.
  if (input.provider === "credentials" && (input.password === null || input.password === undefined)) {
    throw new HttpError(400, "Password is compulsory for credentials provider");
  }

  const existing = await getUserByEmail(input.email);
  if (existing) throw new HttpError(409, "User already exists");

  // Mirror NewUserCreate defaults + validators.
  const authProviders = normalizeAuthProviders([], input.provider);
  const unlockedChapters = await seedUnlockedChapters([]);
  const password =
    input.provider === "credentials" && input.password
      ? await hashPassword(input.password)
      : null;

  const doc: Record<string, unknown> = {
    provider: input.provider,
    email: input.email,
    password,
    googleAccessToken: input.googleAccessToken ?? null,
    firstName: input.firstName ?? null,
    lastName: input.lastName ?? null,
    avatar: input.avatar ?? null,
    status: "Active",
    balance: 0,
    unlockedChapters,
    authProviders,
    subscription: { active: false, expiresAt: null },
    dateCreated: nowIso(),
  };

  const created = await User.create(doc);
  const userId = String(created._id);
  const { accessToken, refreshToken } = await issueTokens(userId);

  // Legacy flowed the doc through UserOut then NewUserOut; toNewUserOut yields
  // the same wire shape (no bookmarks/likes on the signup response — defaults []).
  return toNewUserOut(created.toObject(), { accessToken, refreshToken });
}

// ---------------------------------------------------------------------------
// Sign-in — port of `login` route + `login_credentials` +
// `build_authenticated_user_output`.
// ---------------------------------------------------------------------------
export interface SignInInput {
  provider: "credentials" | "google";
  email: string;
  password?: string | null;
  googleAccessToken?: string | null;
}

export async function loginCredentials(input: SignInInput): Promise<OldUserOut> {
  await db();

  if (input.provider === "google") {
    throw new HttpError(
      400,
      "Google OAuth now uses /api/v1/user/google/auth and /api/v1/user/google/exchange",
    );
  }

  // OldUserBase model_validator: credentials require a password.
  if (input.provider === "credentials" && (input.password === null || input.password === undefined)) {
    throw new HttpError(400, "Password is compulsory for credentials provider");
  }

  const existing = await getCredentialsUserByEmail(input.email);
  if (existing === null) throw new HttpError(404, "User Not Found");

  const hashed = existing.password;
  if (hashed === null || hashed === undefined) {
    throw new HttpError(422, "Password wasn't provided");
  }

  const ok = await checkPassword(String(input.password ?? ""), hashed);
  if (!ok) throw new HttpError(401, "Password Incorrect");

  return buildAuthenticatedUserOutput(existing);
}

/** Port of `build_authenticated_user_output`: issue tokens + hydrate activity. */
export async function buildAuthenticatedUserOutput(userDoc: UserDoc): Promise<OldUserOut> {
  const userId = String(userDoc._id);
  const { accessToken, refreshToken } = await issueTokens(userId);
  const { bookmarks, likes } = await loadUserActivity(userId);
  return toOldUserOut(userDoc, { accessToken, refreshToken, bookmarks, likes });
}

// ---------------------------------------------------------------------------
// Details (with access token) — port of `get_user_details_with_accessToken`.
// Resolves the session row -> user doc, hydrated with bookmarks + likes.
// Returns null when the session row or the user is gone.
// ---------------------------------------------------------------------------
export async function getUserDetailsWithAccessToken(innerId: string): Promise<UserOut | null> {
  await db();
  const row = await getAccessTokenRow(innerId);
  if (!row || typeof row === "string") return null;

  const userId = String(row.userId ?? "");
  const userDoc = await getUserById(userId);
  if (userDoc === null) return null;

  const { bookmarks, likes } = await loadUserActivity(userId);
  return toUserOut(userDoc, { bookmarks, likes });
}

/**
 * Resolve the current user's raw doc from the inner access-token id, or 401.
 * Used by the v2 aggregate/list routes which need `_id`, email, names, etc.
 */
export async function getUserDocOr401(innerId: string): Promise<UserDoc> {
  await db();
  const row = await getAccessTokenRow(innerId);
  if (!row || typeof row === "string") throw new HttpError(401, "Invalid token");
  const userId = String(row.userId ?? "");
  const userDoc = await getUserById(userId);
  if (userDoc === null) throw new HttpError(401, "Invalid token");
  return userDoc;
}

// ---------------------------------------------------------------------------
// Password reset flows — ports of `change_of_user_password_flow1/flow2`.
// ---------------------------------------------------------------------------

/** Initiate: 404 if the user does not exist; else generate + store + email OTP. */
export async function changeOfUserPasswordFlow1(email: string): Promise<void> {
  await db();
  const user = await getUserByEmail(email);
  if (!user) throw new HttpError(404, "User Doesn't exist");
  const otp = generateOtp();
  await storeUserOtp(email, otp);
  await sendPasswordResetOtp({ to: email, otp });
}

/**
 * Conclude: verify OTP -> hash new password -> replace -> revoke all tokens.
 * Returns the legacy boolean result (True on success, False on bad OTP).
 */
export async function changeOfUserPasswordFlow2(
  email: string,
  otp: string,
  password: string,
): Promise<boolean> {
  await db();
  const isValid = await verifyUserOtp(email, otp);
  if (!isValid) return false;

  const hashed = await hashPassword(password);
  const user = await getUserByEmail(email);
  if (!user) {
    // Legacy looked the user up after a successful OTP; absence is unexpected.
    throw new HttpError(400, "Invalid password reset request");
  }
  const userId = String(user._id);
  await User.updateOne({ _id: user._id }, { $set: { password: hashed } });
  await revokeAllTokensForUser(userId);
  return true;
}

// ---------------------------------------------------------------------------
// Profile update — port of `update_user` + `update_user_profile`.
// Updates non-null fields, then re-reads the user as NewUserOut.
// ---------------------------------------------------------------------------
export interface UserUpdateInput {
  firstName?: string | null;
  lastName?: string | null;
  avatar?: string | null;
  status?: "Active" | "Inactive" | "Suspended" | null;
}

export async function updateUser(innerId: string, update: UserUpdateInput): Promise<NewUserOut> {
  await db();

  // Legacy `update_user` first resolves the user from the token; absent -> 404
  // "User Doesn't exist". Then applies the partial (exclude_none) update.
  const current = await getUserDetailsWithAccessToken(innerId);
  if (current === null) throw new HttpError(404, "User Doesn't exist");

  const set: Record<string, unknown> = {};
  if (update.firstName !== null && update.firstName !== undefined) set.firstName = update.firstName;
  if (update.lastName !== null && update.lastName !== undefined) set.lastName = update.lastName;
  if (update.avatar !== null && update.avatar !== undefined) set.avatar = update.avatar;
  if (update.status !== null && update.status !== undefined) set.status = update.status;

  if (Object.keys(set).length > 0 && Types.ObjectId.isValid(current.userId)) {
    await User.updateOne({ _id: new Types.ObjectId(current.userId) }, { $set: set });
  }

  // Re-read (route returns the refreshed user coerced to NewUserOut, keeping the
  // hydrated bookmarks/likes/stopped_reading).
  const userDoc = await getUserById(current.userId);
  if (userDoc === null) throw new HttpError(404, "Details not found");
  const { bookmarks, likes } = await loadUserActivity(current.userId);
  return toNewUserOut(userDoc, { bookmarks, likes });
}
