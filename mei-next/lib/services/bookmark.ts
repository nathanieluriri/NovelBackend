/**
 * Bookmark service — port of `services/bookmark_services.py`
 * (+ `repositories/bookmark_repo.py`) for the v2 `/api/v2/bookmark/*` surface.
 *
 * Behavioural parity notes (reproduced EXACTLY — do not "fix"):
 *  - LIST by user: optional `targetType` filter, sorted `dateCreated` DESC
 *    (legacy index `{userId, dateCreated:-1}`; the FastAPI find used the index
 *    ordering). Each item hydrates `chapterSummary` from the summary cache when
 *    `chapterId` is present. `pageNumber` is NOT looked up — it stays null
 *    (legacy `BookMarkOut` never populated it from a DB read).
 *  - CREATE: `BookMarkCreateRequest` normalizes legacy `pageId`-only payloads to
 *    `targetType="page"`, `targetId=pageId` (done at the route's zod layer);
 *    here we validate `targetId` is 24 chars (422 otherwise), reject duplicates
 *    per the unique `{userId,targetType,targetId}` index (409), and verify the
 *    target entity exists (404 Book/Chapter/Page not found). For `chapter`/`page`
 *    targets we hydrate `chapterLabel` + `chapterId`; the response then hydrates
 *    `chapterSummary`.
 *  - REMOVE: delete by `{_id, userId}` (scoped to the caller). 404 when nothing
 *    was deleted ("Resource already deleted"); otherwise return the removed doc
 *    serialized (with `chapterSummary` hydrated).
 *
 * Models are imported DIRECTLY (CONVENTIONS.md: this slice may touch Bookmark /
 * Book / Chapter / Page; it must NOT import other domain services). Actor
 * identity is resolved from the access-token row (member.userId == row.userId ==
 * admin.userId — exactly what legacy `_get_actor_user_id` returned).
 */
import { Types } from "mongoose";

import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { getAccessTokenRow, type Claims } from "@/lib/auth";
import { getChapterSummary } from "@/lib/cache/summary";
import {
  Bookmark,
  Book,
  Chapter,
  Page,
  type BookmarkDoc,
} from "@/lib/models";
import {
  toBookmarkOut,
  type BookMarkOutAsync,
  type InteractionTargetType,
} from "@/lib/serializers";

/* eslint-disable @typescript-eslint/no-explicit-any */
type AnyDoc = Record<string, any>;

const TARGET_TYPES: readonly string[] = ["book", "chapter", "page"];

/**
 * Resolve the calling actor's userId — the port of legacy `_get_actor_user_id`.
 * For both members and admins this is the `userId` stored on the access-token
 * row (member.userId / admin.userId both came from this row). 401 when the
 * session row is gone or not yet active.
 */
export async function resolveActorUserId(claims: Claims): Promise<string> {
  await db();
  const row = await getAccessTokenRow(claims.accessToken);
  if (!row || typeof row === "string") throw new HttpError(401, "Invalid token");
  const userId = String(row.userId ?? "");
  if (!userId) throw new HttpError(401, "Invalid token");
  return userId;
}

/** Coerce an arbitrary string to the InteractionTargetType filter, or null. */
export function parseTargetType(raw: string | null): InteractionTargetType | null {
  if (raw === null) return null;
  if (!TARGET_TYPES.includes(raw)) {
    // Legacy FastAPI coerced the query param via the InteractionTargetType enum;
    // an invalid value is a 422 validation error there.
    throw new HttpError(422, "targetType must be one of: book, chapter, page");
  }
  return raw as InteractionTargetType;
}

function toObjectIdOrNull(id: string): Types.ObjectId | null {
  return Types.ObjectId.isValid(id) ? new Types.ObjectId(id) : null;
}

/** Hydrate `chapterSummary` from the summary cache when the doc carries a chapterId. */
async function toBookmarkOutHydrated(doc: AnyDoc): Promise<BookMarkOutAsync> {
  const chapterId = doc.chapterId ? String(doc.chapterId) : "";
  const summary = chapterId ? await getChapterSummary(chapterId) : null;
  return toBookmarkOut(doc, { chapterSummary: summary });
}

// ---------------------------------------------------------------------------
// LIST + COUNT — ports of `retrieve_user_bookmark` / `retrieve_user_bookmark_count`
// (+ `get_all_user_bookmarks` / `count_user_bookmarks`).
// ---------------------------------------------------------------------------

/**
 * Bookmarks for `userId`, optionally filtered by `targetType`, paginated and
 * sorted `dateCreated` DESC. Each hydrated with `chapterSummary`.
 */
export async function retrieveUserBookmark(
  userId: string,
  targetType: InteractionTargetType | null = null,
  skip = 0,
  limit = 20,
): Promise<BookMarkOutAsync[]> {
  await db();
  const query: Record<string, unknown> = { userId };
  if (targetType !== null) query.targetType = targetType;
  const docs = await Bookmark.find(query)
    .sort({ dateCreated: -1 })
    .skip(skip)
    .limit(limit)
    .lean<BookmarkDoc[]>();
  const out: BookMarkOutAsync[] = [];
  for (const doc of docs) {
    out.push(await toBookmarkOutHydrated(doc));
  }
  return out;
}

/** Count of `userId`'s bookmarks, optionally filtered by `targetType`. */
export async function retrieveUserBookmarkCount(
  userId: string,
  targetType: InteractionTargetType | null = null,
): Promise<number> {
  await db();
  const query: Record<string, unknown> = { userId };
  if (targetType !== null) query.targetType = targetType;
  return Bookmark.countDocuments(query);
}

// ---------------------------------------------------------------------------
// CREATE — port of `create_bookmark_for_target` + `_build_bookmark_model`.
// ---------------------------------------------------------------------------

export interface BookmarkCreateInput {
  targetType: InteractionTargetType | null;
  targetId: string | null;
  pageId?: string | null;
}

/**
 * Build the bookmark document for a target, validating that the target exists.
 *  - book    → 404 "Book not found"; no chapterId/chapterLabel.
 *  - chapter → 404 "Chapter not found"; chapterId = targetId, chapterLabel.
 *  - page    → 404 "Page not found"; chapterId = page.chapterId, chapterLabel
 *              taken from that chapter (null if the chapter is gone), pageId.
 */
async function buildBookmarkModel(
  userId: string,
  targetType: InteractionTargetType,
  targetId: string,
): Promise<Record<string, unknown>> {
  if (targetType === "book") {
    const oid = toObjectIdOrNull(targetId);
    const book = oid ? await Book.findById(oid).lean<AnyDoc>() : null;
    if (book === null) throw new HttpError(404, "Book not found");
    return { userId, targetType, targetId };
  }

  if (targetType === "chapter") {
    const oid = toObjectIdOrNull(targetId);
    const chapter = oid ? await Chapter.findById(oid).lean<AnyDoc>() : null;
    if (chapter === null) throw new HttpError(404, "Chapter not found");
    return {
      userId,
      targetType,
      targetId,
      chapterId: targetId,
      chapterLabel: chapter.chapterLabel ?? null,
    };
  }

  // page
  const oid = toObjectIdOrNull(targetId);
  const page = oid ? await Page.findById(oid).lean<AnyDoc>() : null;
  if (page === null) throw new HttpError(404, "Page not found");
  const pageChapterId = page.chapterId ? String(page.chapterId) : null;
  let chapterLabel: string | null = null;
  if (pageChapterId) {
    const chapterOid = toObjectIdOrNull(pageChapterId);
    const chapter = chapterOid ? await Chapter.findById(chapterOid).lean<AnyDoc>() : null;
    chapterLabel = chapter ? (chapter.chapterLabel ?? null) : null;
  }
  return {
    userId,
    targetType,
    targetId,
    pageId: targetId,
    chapterId: pageChapterId,
    chapterLabel,
  };
}

/**
 * Create a bookmark for the caller. Mirrors `create_bookmark_for_target`:
 *  1. require targetType + targetId (422 when missing — defends against a
 *     pre-normalized payload reaching the service).
 *  2. 409 when an identical `{userId,targetType,targetId}` already exists.
 *  3. validate + build the target-specific document (404 if the target is gone).
 *  4. insert, then serialize with a hydrated `chapterSummary`.
 */
export async function createBookmarkForTarget(
  userId: string,
  request: BookmarkCreateInput,
): Promise<BookMarkOutAsync> {
  await db();

  if (request.targetType === null || request.targetId === null) {
    throw new HttpError(422, "targetType and targetId are required");
  }
  if (request.targetId.length !== 24) {
    throw new HttpError(422, "targetId must be exactly 24 characters long");
  }

  const existing = await Bookmark.findOne({
    userId,
    targetType: request.targetType,
    targetId: request.targetId,
  }).lean<BookmarkDoc>();
  if (existing !== null) throw new HttpError(409, "Bookmark already exists");

  const model = await buildBookmarkModel(userId, request.targetType, request.targetId);
  const created = await Bookmark.create(model);
  const createdDoc = (created.toObject ? created.toObject() : created) as BookmarkDoc;
  return toBookmarkOutHydrated(createdDoc);
}

// ---------------------------------------------------------------------------
// REMOVE — port of `remove_bookmark_for_user` (+ `delete_bookmark_by_id_userId`).
// ---------------------------------------------------------------------------

/**
 * Delete the caller's bookmark by id (scoped to `userId`). Returns null when no
 * matching doc exists (an invalid id or another user's bookmark also yields
 * null) so the route can raise 404 "Resource already deleted". On success the
 * removed doc is serialized with a hydrated `chapterSummary`.
 */
export async function removeBookmarkForUser(
  bookmarkId: string,
  userId: string,
): Promise<BookMarkOutAsync | null> {
  await db();
  const oid = toObjectIdOrNull(bookmarkId);
  if (oid === null) return null;
  const removed = await Bookmark.findOneAndDelete({ _id: oid, userId }).lean<BookmarkDoc>();
  if (removed === null) return null;
  return toBookmarkOutHydrated(removed);
}
