/**
 * Like service — port of `services/like_services.py` (+ `repositories/like_repo.py`)
 * for the v2 `/api/v2/like/*` surface.
 *
 * Behavioural parity notes (reproduced EXACTLY — do not "fix"):
 *  - LIST by user (`/like/get`): the caller's likes, paginated; each item
 *    hydrates `chapterSummary` from the summary cache when `chapterId` is present
 *    (legacy `retrieve_user_likes` does a per-like `get_chapter_summary`).
 *  - LIST by chapter (`/like/get/{chapterId}`): all likes on the chapter with the
 *    liking user's details. The chapter summary is fetched ONCE and shared across
 *    every item (legacy `retrieve_chapter_likes_with_user_details`); user details
 *    are batch-fetched (one `$in` query) to avoid an N+1 — missing users → null.
 *  - ADMIN chapter interaction users (`/like/admin/get/chapter/{id}/users`): the
 *    chapter MUST exist first (404 "Chapter not found"); then a `$group` by
 *    `userId` yields `interactionCount` (sum) + `lastInteractionAt` (max
 *    dateCreated), sorted `lastInteractionAt` DESC then `_id` ASC, paginated.
 *    User details are batch-fetched and hydrated.
 *  - CREATE (`/like/create`): the chapter MUST exist first (404 "Chapter not
 *    found"); `chapaterLabel` (sic) is copied off `chapter.chapterLabel`. Insert
 *    is idempotent on the unique `{userId, chapterId}` index — a duplicate returns
 *    the existing like rather than erroring (legacy `create_like` swallows the
 *    DuplicateKeyError and re-reads). The result hydrates `chapterSummary`.
 *  - REMOVE (`/like/remove/{likeId}`): delete by `_id`. Returns null when nothing
 *    was deleted (an invalid id also yields null) so the route raises 404
 *    "Resource already deleted". On success the removed doc is serialized with a
 *    hydrated `chapterSummary`.
 *
 * Models are imported DIRECTLY (CONVENTIONS.md: this slice may touch Like /
 * Chapter / User; it must NOT import other domain services). Actor identity is
 * resolved from the access-token row (member.userId == row.userId ==
 * admin.userId — exactly what legacy `_get_actor_user_id` returned).
 */
import { Types } from "mongoose";

import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { getAccessTokenRow, type Claims } from "@/lib/auth";
import { getChapterSummary } from "@/lib/cache/summary";
import { Like, Chapter, User, type LikeDoc } from "@/lib/models";
import {
  toLikeOut,
  toLikeWithUserOut,
  toChapterInteractionUserOut,
  type LikeOut,
  type LikeWithUserOut,
  type ChapterInteractionUserOut,
} from "@/lib/serializers";

/* eslint-disable @typescript-eslint/no-explicit-any */
type AnyDoc = Record<string, any>;

const OBJECT_ID_RE = /^[a-fA-F0-9]{24}$/;

function toObjectIdOrNull(id: string): Types.ObjectId | null {
  return Types.ObjectId.isValid(id) ? new Types.ObjectId(id) : null;
}

/**
 * Resolve the calling actor's userId — the port of legacy `_get_actor_user_id`.
 * For both members and admins this is the `userId` on the access-token row.
 * 401 when the session row is gone or not yet active.
 */
export async function resolveActorUserId(claims: Claims): Promise<string> {
  await db();
  const row = await getAccessTokenRow(claims.accessToken);
  if (!row || typeof row === "string") throw new HttpError(401, "Invalid token");
  const userId = String(row.userId ?? "");
  if (!userId) throw new HttpError(401, "Invalid token");
  return userId;
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/**
 * Batch-fetch users by their string userIds (the port of `get_users_by_user_ids`):
 * only valid 24-hex ids are queried, deduped via the `$in`, and returned keyed by
 * `String(_id)` so callers can hydrate by `like.userId`.
 */
async function fetchUserMap(userIds: string[]): Promise<Map<string, AnyDoc>> {
  const objectIds = userIds
    .filter((uid) => uid && OBJECT_ID_RE.test(uid))
    .map((uid) => new Types.ObjectId(uid));
  const map = new Map<string, AnyDoc>();
  if (objectIds.length === 0) return map;
  const users = await User.find({ _id: { $in: objectIds } }).lean<AnyDoc[]>();
  for (const user of users) {
    map.set(String(user._id), user);
  }
  return map;
}

/**
 * Ensure the chapter exists (port of `_ensure_chapter_exists` /
 * `fetch_chapter_with_chapterId`): an invalid id behaves like "not found".
 * Returns the chapter doc; raises 404 "Chapter not found" otherwise.
 */
async function ensureChapterExists(chapterId: string): Promise<AnyDoc> {
  const oid = toObjectIdOrNull(chapterId);
  const chapter = oid ? await Chapter.findById(oid).lean<AnyDoc>() : null;
  if (chapter === null) throw new HttpError(404, "Chapter not found");
  return chapter;
}

// ---------------------------------------------------------------------------
// LIST: caller's likes + count — ports of `retrieve_user_likes` /
// `retrieve_user_likes_count` (+ `get_all_user_likes` / `count_user_likes`).
// ---------------------------------------------------------------------------

/** The caller's likes, paginated; each hydrated with its own `chapterSummary`. */
export async function retrieveUserLikes(
  userId: string,
  skip = 0,
  limit = 20,
): Promise<LikeOut[]> {
  await db();
  const docs = await Like.find({ userId }).skip(skip).limit(limit).lean<LikeDoc[]>();
  const out: LikeOut[] = [];
  for (const doc of docs) {
    const chapterId = doc.chapterId ? String(doc.chapterId) : "";
    const summary = chapterId ? await getChapterSummary(chapterId) : null;
    out.push(toLikeOut(doc, summary));
  }
  return out;
}

/** Count of the caller's likes. */
export async function retrieveUserLikesCount(userId: string): Promise<number> {
  await db();
  return Like.countDocuments({ userId });
}

// ---------------------------------------------------------------------------
// LIST: chapter likes with user details + count — ports of
// `retrieve_chapter_likes_with_user_details` / `retrieve_chapter_likes_count`.
// ---------------------------------------------------------------------------

/**
 * All likes on a chapter with the liking user's details, paginated. The chapter
 * summary is fetched ONCE and shared across items; users are batch-fetched (one
 * `$in` query) to avoid an N+1. A like whose user is gone gets `user: null`.
 */
export async function retrieveChapterLikesWithUserDetails(
  chapterId: string,
  skip = 0,
  limit = 20,
): Promise<LikeWithUserOut[]> {
  await db();
  const docs = await Like.find({ chapterId }).skip(skip).limit(limit).lean<LikeDoc[]>();
  const chapterSummary = await getChapterSummary(chapterId);

  const uniqueUserIds = Array.from(
    new Set(docs.map((d) => (d.userId ? String(d.userId) : "")).filter((u) => u)),
  );
  const userMap = await fetchUserMap(uniqueUserIds);

  return docs.map((doc) => {
    const user = doc.userId ? userMap.get(String(doc.userId)) ?? null : null;
    return toLikeWithUserOut(doc, user, chapterSummary);
  });
}

/** Count of all likes on a chapter. */
export async function retrieveChapterLikesCount(chapterId: string): Promise<number> {
  await db();
  return Like.countDocuments({ chapterId });
}

// ---------------------------------------------------------------------------
// ADMIN: chapter interaction users aggregation + count — ports of
// `retrieve_chapter_like_users` / `retrieve_chapter_like_users_count`.
// ---------------------------------------------------------------------------

/**
 * Per-user like-interaction rollup for a chapter (chapter must exist → 404).
 * `$group` by `userId`: `interactionCount` = count, `lastInteractionAt` = max
 * `dateCreated`; sorted `lastInteractionAt` DESC then `_id` ASC; paginated.
 * User details are batch-fetched and hydrated; rows with a null group `_id`
 * are dropped (legacy filters `row["_id"] is not None`).
 */
export async function retrieveChapterLikeUsers(
  chapterId: string,
  skip = 0,
  limit = 20,
): Promise<ChapterInteractionUserOut[]> {
  await db();
  await ensureChapterExists(chapterId);

  const stats = await Like.aggregate<{
    _id: string | null;
    interactionCount: number;
    lastInteractionAt: unknown;
  }>([
    { $match: { chapterId } },
    {
      $group: {
        _id: "$userId",
        interactionCount: { $sum: 1 },
        lastInteractionAt: { $max: "$dateCreated" },
      },
    },
    { $sort: { lastInteractionAt: -1, _id: 1 } },
    { $skip: skip },
    { $limit: limit },
  ]);

  const rows = stats.filter((row) => row._id !== null && row._id !== undefined);
  const userIds = rows.map((row) => String(row._id));
  const userMap = await fetchUserMap(userIds);

  return rows.map((row) => {
    const uid = String(row._id);
    const user = userMap.get(uid) ?? {};
    return toChapterInteractionUserOut(
      { ...user, userId: uid },
      row.interactionCount,
      (row.lastInteractionAt as string | number | Date | null | undefined) ?? null,
    );
  });
}

/** Distinct-user count for a chapter's likes (chapter must exist → 404). */
export async function retrieveChapterLikeUsersCount(chapterId: string): Promise<number> {
  await db();
  await ensureChapterExists(chapterId);

  const result = await Like.aggregate<{ total: number }>([
    { $match: { chapterId } },
    { $group: { _id: "$userId" } },
    { $count: "total" },
  ]);
  if (result.length === 0) return 0;
  return Number(result[0].total ?? 0);
}

// ---------------------------------------------------------------------------
// CREATE — port of `add_like` (+ `create_like`).
// ---------------------------------------------------------------------------

/**
 * Create a like for the caller on a chapter. Mirrors `add_like`:
 *  1. the chapter MUST exist (404 "Chapter not found"); `chapaterLabel` (sic) is
 *     copied off `chapter.chapterLabel`.
 *  2. insert; on the unique `{userId, chapterId}` collision return the EXISTING
 *     like (idempotent — legacy swallows the DuplicateKeyError and re-reads).
 *  3. serialize with a hydrated `chapterSummary`.
 */
export async function addLike(
  userId: string,
  role: string,
  chapterId: string,
): Promise<LikeOut> {
  await db();
  const chapter = await ensureChapterExists(chapterId);

  // `chapaterLabel` is a required storage field; legacy copies the chapter label
  // verbatim (coerced to "" when the chapter has no label).
  const chapaterLabel = chapter.chapterLabel == null ? "" : String(chapter.chapterLabel);

  let likeDoc: LikeDoc;
  try {
    const created = await Like.create({
      chapterId,
      userId,
      role,
      likeType: "Liked Chapter",
      chapaterLabel,
      dateCreated: new Date().toISOString(),
    });
    likeDoc = (created.toObject ? created.toObject() : created) as LikeDoc;
  } catch (err) {
    if (isDuplicateKeyError(err)) {
      const existing = await Like.findOne({ userId, chapterId }).lean<LikeDoc>();
      if (existing === null) throw err;
      likeDoc = existing;
    } else {
      throw err;
    }
  }

  const summary = likeDoc.chapterId ? await getChapterSummary(String(likeDoc.chapterId)) : null;
  return toLikeOut(likeDoc, summary);
}

function isDuplicateKeyError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    (err as { code?: unknown }).code === 11000
  );
}

// ---------------------------------------------------------------------------
// REMOVE — port of `remove_like` (+ `delete_like_with_like_id`).
// ---------------------------------------------------------------------------

/**
 * Delete a like by id. Returns null when no matching doc exists (an invalid id
 * also yields null) so the route can raise 404 "Resource already deleted". On
 * success the removed doc is serialized with a hydrated `chapterSummary`.
 *
 * Note: this endpoint is PUBLIC (no-auth) and removal is by `likeId` only — NOT
 * scoped to a user — exactly as legacy `delete_like_with_like_id`.
 */
export async function removeLike(likeId: string): Promise<LikeOut | null> {
  await db();
  const oid = toObjectIdOrNull(likeId);
  if (oid === null) return null;
  const removed = await Like.findOneAndDelete({ _id: oid }).lean<LikeDoc>();
  if (removed === null) return null;
  const summary = removed.chapterId ? await getChapterSummary(String(removed.chapterId)) : null;
  return toLikeOut(removed, summary);
}
