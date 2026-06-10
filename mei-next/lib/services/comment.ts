/**
 * Comment service — port of `services/comments_services.py`
 * (+ `repositories/comments_repo.py`) for the v2 `/api/v2/comment/*` surface.
 *
 * Behavioural parity notes (reproduced EXACTLY — do not "fix"):
 *  - LIST by target (`/comment/get` paired, `/comment/get/target/...`,
 *    `/comment/get/{chapterId}`): all comments on a target, paginated. For a
 *    `chapter` target the query carries the legacy OR-fallback
 *    (`{targetType:"chapter", targetId} OR {chapterId}`) so chapter-only rows
 *    that predate the generic target model are still readable — mirror of
 *    `_target_query`. User details (firstName/lastName/avatar/email) are hydrated
 *    per item; here they are batch-fetched (one `$in`) to avoid the legacy N+1
 *    while producing the identical wire shape (legacy hydrated each `CommentOut`
 *    individually in `model_async_validate`).
 *  - LIST by user (`/comment/get` unpaired): the caller's comments, paginated;
 *    same per-item user hydration.
 *  - COUNTS mirror the list queries exactly (same OR-fallback for chapter).
 *  - CREATE (`/comment/create`): the target MUST exist first (404
 *    "Book/Chapter/Page not found"); `targetType`+`targetId` are required (422 if
 *    a pre-normalized payload reaches the service). `role` comes from the JWT
 *    claim, `userId` from the access-token row — exactly legacy `_get_actor`.
 *  - UPDATE (`/comment/update`): scoped to `{_id, userId}` (own comment only —
 *    legacy `update_comment_with_comment_id` matches userId). Returns null when
 *    nothing matched (invalid id / not the owner / gone) so the route raises 404
 *    "Resource already deleted".
 *  - USER REMOVE (`/comment/user/remove/{id}`): delete by `{_id, userId}` (own
 *    only). ADMIN REMOVE (`/comment/admin/remove/{id}`): delete by `_id` (any).
 *    Both return null when nothing was deleted → route 404 "Resource already
 *    deleted".
 *  - ADMIN chapter interaction users (`/comment/admin/get/chapter/{id}/users`):
 *    the chapter MUST exist first (404 "Chapter not found"); a `$group` by
 *    `userId` over the OR-fallback chapter query yields `interactionCount` (sum)
 *    + `lastInteractionAt` (max dateCreated), sorted `lastInteractionAt` DESC then
 *    `_id` ASC, paginated. Rows with a null group `_id` are dropped. User details
 *    are batch-fetched and hydrated. Implemented LOCALLY (not imported from the
 *    like service) — the like service's aggregation lacks the chapter OR-fallback.
 *
 * Models are imported DIRECTLY (CONVENTIONS.md: this slice may touch Comment /
 * Book / Chapter / Page / User; it must NOT import other domain services). Actor
 * identity is resolved from the access-token row (member.userId == row.userId ==
 * admin.userId — exactly what legacy `_get_actor` returned).
 */
import { Types } from "mongoose";

import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { getAccessTokenRow, type Claims } from "@/lib/auth";
import {
  Comment,
  Book,
  Chapter,
  Page,
  User,
  type CommentDoc,
} from "@/lib/models";
import {
  toCommentOut,
  toChapterInteractionUserOut,
  type CommentOut,
  type CommentUserDetails,
  type InteractionTargetType,
  type ChapterInteractionUserOut,
} from "@/lib/serializers";

/* eslint-disable @typescript-eslint/no-explicit-any */
type AnyDoc = Record<string, any>;

const OBJECT_ID_RE = /^[a-fA-F0-9]{24}$/;

function toObjectIdOrNull(id: string): Types.ObjectId | null {
  return Types.ObjectId.isValid(id) ? new Types.ObjectId(id) : null;
}

/**
 * Resolve the calling actor's userId — the port of legacy `_get_actor`.
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
 * Batch-fetch users by their string userIds (the port of `get_users_by_user_ids`
 * + the per-comment `set_user_details`): only valid 24-hex ids are queried,
 * deduped via the `$in`, and returned keyed by `String(_id)` so callers can
 * hydrate by `comment.userId`. Missing users hydrate to a record of nulls.
 */
async function fetchUserMap(userIds: string[]): Promise<Map<string, AnyDoc>> {
  const objectIds = Array.from(new Set(userIds.filter((uid) => uid && OBJECT_ID_RE.test(uid)))).map(
    (uid) => new Types.ObjectId(uid),
  );
  const map = new Map<string, AnyDoc>();
  if (objectIds.length === 0) return map;
  const users = await User.find(
    { _id: { $in: objectIds } },
    { firstName: 1, lastName: 1, avatar: 1, email: 1 },
  ).lean<AnyDoc[]>();
  for (const user of users) {
    map.set(String(user._id), user);
  }
  return map;
}

/** Serialize comments, hydrating each with its batch-fetched user details. */
async function serializeWithUsers(docs: CommentDoc[]): Promise<CommentOut[]> {
  const userIds = docs.map((d) => (d.userId ? String(d.userId) : "")).filter((u) => u);
  const userMap = await fetchUserMap(userIds);
  return docs.map((doc) => {
    const user = doc.userId ? userMap.get(String(doc.userId)) : undefined;
    const details: CommentUserDetails | undefined = user
      ? {
          firstName: user.firstName,
          lastName: user.lastName,
          avatar: user.avatar,
          email: user.email,
        }
      : undefined;
    return toCommentOut(doc, details);
  });
}

/**
 * The legacy `_target_query`: chapter comments predate the generic target model,
 * so the `$or` fallback keeps legacy rows (`chapterId`) readable alongside the
 * new `{targetType, targetId}` shape. Non-chapter targets use the plain query.
 */
function targetQuery(targetType: InteractionTargetType, targetId: string): Record<string, unknown> {
  if (targetType === "chapter") {
    return {
      $or: [
        { targetType: "chapter", targetId },
        { chapterId: targetId },
      ],
    };
  }
  return { targetType, targetId };
}

/**
 * Ensure the comment target exists (port of `_ensure_target_exists`): an invalid
 * id behaves like "not found". 404 message capitalizes the target type
 * ("Book not found" / "Chapter not found" / "Page not found").
 */
async function ensureTargetExists(targetType: InteractionTargetType, targetId: string): Promise<void> {
  const oid = toObjectIdOrNull(targetId);
  let target: AnyDoc | null = null;
  if (oid !== null) {
    if (targetType === "book") {
      target = await Book.findById(oid).lean<AnyDoc>();
    } else if (targetType === "chapter") {
      target = await Chapter.findById(oid).lean<AnyDoc>();
    } else {
      target = await Page.findById(oid).lean<AnyDoc>();
    }
  }
  if (target === null) {
    const label = targetType.charAt(0).toUpperCase() + targetType.slice(1);
    throw new HttpError(404, `${label} not found`);
  }
}

// ---------------------------------------------------------------------------
// LIST: caller's comments + count — ports of `retrieve_user_comments` /
// `retrieve_user_comments_count` (+ `get_all_user_comments` / `count_all_user_comments`).
// ---------------------------------------------------------------------------

/** The caller's comments, paginated; each hydrated with its user details. */
export async function retrieveUserComments(
  userId: string,
  skip = 0,
  limit = 20,
): Promise<CommentOut[]> {
  await db();
  const docs = await Comment.find({ userId }).skip(skip).limit(limit).lean<CommentDoc[]>();
  return serializeWithUsers(docs);
}

/** Count of the caller's comments. */
export async function retrieveUserCommentsCount(userId: string): Promise<number> {
  await db();
  return Comment.countDocuments({ userId });
}

// ---------------------------------------------------------------------------
// LIST: target comments + count — ports of `retrieve_target_comments` /
// `retrieve_target_comments_count` (+ `get_comments_by_target` / `count_comments_by_target`).
// ---------------------------------------------------------------------------

/**
 * All comments on a target, paginated; each hydrated with its user details. For
 * a `chapter` target the legacy OR-fallback query includes chapter-only rows.
 */
export async function retrieveTargetComments(
  targetType: InteractionTargetType,
  targetId: string,
  skip = 0,
  limit = 20,
): Promise<CommentOut[]> {
  await db();
  const docs = await Comment.find(targetQuery(targetType, targetId))
    .skip(skip)
    .limit(limit)
    .lean<CommentDoc[]>();
  return serializeWithUsers(docs);
}

/** Count of all comments on a target (same OR-fallback for chapter). */
export async function retrieveTargetCommentsCount(
  targetType: InteractionTargetType,
  targetId: string,
): Promise<number> {
  await db();
  return Comment.countDocuments(targetQuery(targetType, targetId));
}

// ---------------------------------------------------------------------------
// CREATE — port of `add_comment_for_target` (+ `create_comment`).
// ---------------------------------------------------------------------------

export interface CommentCreateInput {
  text: string;
  targetType: InteractionTargetType | null;
  targetId: string | null;
  parentCommentId?: string | null;
  commentType?: string | null;
}

/**
 * Create a comment for the caller on a target. Mirrors `add_comment_for_target`:
 *  1. require targetType + targetId (422 — defends against a pre-normalized
 *     payload reaching the service).
 *  2. the target MUST exist (404 "Book/Chapter/Page not found").
 *  3. insert with `role` (from the JWT claim) + `userId` (from the access row),
 *     `dateCreated` set to now.
 *  4. serialize with the caller's hydrated user details.
 */
export async function addCommentForTarget(
  userId: string,
  role: string,
  request: CommentCreateInput,
): Promise<CommentOut> {
  await db();

  if (request.targetType === null || request.targetId === null) {
    throw new HttpError(422, "targetType and targetId are required");
  }
  await ensureTargetExists(request.targetType, request.targetId);

  const created = await Comment.create({
    userId,
    role,
    text: request.text,
    targetType: request.targetType,
    targetId: request.targetId,
    parentCommentId: request.parentCommentId ?? null,
    commentType: request.commentType ?? "reply_target",
    dateCreated: new Date().toISOString(),
  });
  const createdDoc = (created.toObject ? created.toObject() : created) as CommentDoc;

  const [out] = await serializeWithUsers([createdDoc]);
  return out;
}

// ---------------------------------------------------------------------------
// UPDATE — port of `update_comment` (+ `update_comment_with_comment_id`).
// ---------------------------------------------------------------------------

/**
 * Update the caller's comment text (scoped to `{_id, userId}` — own comment
 * only). Returns null when nothing matched (invalid id / not the owner / gone)
 * so the route can raise 404 "Resource already deleted". On success the updated
 * doc is serialized with the caller's hydrated user details.
 */
export async function updateComment(
  commentId: string,
  userId: string,
  text: string,
): Promise<CommentOut | null> {
  await db();
  const oid = toObjectIdOrNull(commentId);
  if (oid === null) return null;
  await Comment.updateOne({ _id: oid, userId }, { $set: { text } });
  const updated = await Comment.findOne({ _id: oid, userId }).lean<CommentDoc>();
  if (updated === null) return null;
  const [out] = await serializeWithUsers([updated]);
  return out;
}

// ---------------------------------------------------------------------------
// REMOVE — ports of `remove_comment_by_userId_and_commentId` (user-scoped) and
// `remove_comment` (admin, by id).
// ---------------------------------------------------------------------------

/**
 * Delete the caller's comment by id (scoped to `{_id, userId}` — own only).
 * Returns null when nothing was deleted (invalid id / not the owner / already
 * gone) so the route can raise 404 "Resource already deleted". On success the
 * removed doc is serialized with its hydrated user details.
 */
export async function removeCommentByUserIdAndCommentId(
  commentId: string,
  userId: string,
): Promise<CommentOut | null> {
  await db();
  const oid = toObjectIdOrNull(commentId);
  if (oid === null) return null;
  const removed = await Comment.findOneAndDelete({ _id: oid, userId }).lean<CommentDoc>();
  if (removed === null) return null;
  const [out] = await serializeWithUsers([removed]);
  return out;
}

/**
 * Delete a comment by id (admin — not scoped to a user). Returns null when no
 * matching doc exists (an invalid id also yields null) so the route can raise
 * 404 "Resource already deleted". On success the removed doc is serialized with
 * its hydrated user details.
 */
export async function removeComment(commentId: string): Promise<CommentOut | null> {
  await db();
  const oid = toObjectIdOrNull(commentId);
  if (oid === null) return null;
  const removed = await Comment.findOneAndDelete({ _id: oid }).lean<CommentDoc>();
  if (removed === null) return null;
  const [out] = await serializeWithUsers([removed]);
  return out;
}

// ---------------------------------------------------------------------------
// ADMIN: chapter interaction users aggregation + count — ports of
// `retrieve_chapter_comment_users` / `retrieve_chapter_comment_users_count`
// (+ `get_chapter_comment_user_stats` / `count_chapter_comment_users`).
// Implemented LOCALLY (the chapter OR-fallback differs from the like service).
// ---------------------------------------------------------------------------

/**
 * Per-user comment-interaction rollup for a chapter (chapter must exist → 404).
 * `$match` uses the OR-fallback chapter query; `$group` by `userId`:
 * `interactionCount` = count, `lastInteractionAt` = max `dateCreated`; sorted
 * `lastInteractionAt` DESC then `_id` ASC; paginated. Rows with a null group
 * `_id` are dropped. User details are batch-fetched and hydrated.
 */
export async function retrieveChapterCommentUsers(
  chapterId: string,
  skip = 0,
  limit = 20,
): Promise<ChapterInteractionUserOut[]> {
  await db();
  await ensureTargetExists("chapter", chapterId);

  const stats = await Comment.aggregate<{
    _id: string | null;
    interactionCount: number;
    lastInteractionAt: unknown;
  }>([
    { $match: targetQuery("chapter", chapterId) },
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

/** Distinct-user count for a chapter's comments (chapter must exist → 404). */
export async function retrieveChapterCommentUsersCount(chapterId: string): Promise<number> {
  await db();
  await ensureTargetExists("chapter", chapterId);

  const result = await Comment.aggregate<{ total: number }>([
    { $match: targetQuery("chapter", chapterId) },
    { $group: { _id: "$userId" } },
    { $count: "total" },
  ]);
  if (result.length === 0) return 0;
  return Number(result[0].total ?? 0);
}
