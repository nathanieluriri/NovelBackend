/**
 * Reaction service — port of `services/reaction_service.py`
 * (+ `repositories/reaction.py`) for the v2 `/api/v2/reactions/*` surface.
 *
 * One reaction per `(userId, authorRoomId)` (unique index). Dates are stored as
 * EPOCH SECONDS; the serializer (`toReactionOut`) maps them to ISO
 * `dateCreated`/`lastUpdated` `+00:00` strings (schema.md §0.4).
 *
 * Access gating (legacy `_ensure_reaction_access`, used by create/update/delete):
 *  1. author room exists — invalid id → 400 "Invalid author_room ID format";
 *     missing → 404 "AuthorRoom not found".
 *  2. its chapter exists (lookup by `_id`) → 404 "Chapter not found".
 *  3. caller is a real member — invalid ObjectId userId / missing user → 401
 *     "Invalid token" (legacy raises 401 here, NOT 400).
 *  4. `hasChapterAccess` (via @/lib/services/access) else → 403 "You do not have
 *     access to react to this chapter".
 *
 * Behavioural parity (reproduced EXACTLY — do not "fix"):
 *  - CREATE (`add_reaction`): ensure access → if the caller already reacted,
 *    REPLACE the existing reaction (update in place); else insert. A racing
 *    duplicate on the unique `{userId,authorRoomId}` index surfaces as 409 "You
 *    have already reacted to this author room" (legacy `create_reaction`).
 *  - GET (`retrieve_reaction_by_user_and_room`): the caller's reaction; 404
 *    "Reaction not found for user in this room" when absent. NO access gate
 *    (legacy GET path never calls `_ensure_reaction_access`).
 *  - UPDATE (`update_reaction_by_id`): `reaction` required → 400 "reaction is
 *    required" when null; ensure access; existing (404); update by `_id` (404 on
 *    failure). `last_updated` auto-refreshed.
 *  - DELETE (`remove_reaction_for_user`): ensure access; existing (404); delete
 *    by `_id` (404 if nothing removed); returns true.
 *
 * Models (Reaction, AuthorRoom, Chapter, User) are imported DIRECTLY; access
 * gating is consumed from the `@/lib/services/access` seam (legacy
 * `has_chapter_access`).
 */
import { Types } from "mongoose";

import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { hasChapterAccess } from "@/lib/services/access";
import {
  Reaction,
  AuthorRoom,
  Chapter,
  User,
  type ReactionDoc,
  type UserDoc,
  type ChapterDoc,
} from "@/lib/models";
import { toReactionOut, type ReactionOut } from "@/lib/serializers";

/* eslint-disable @typescript-eslint/no-explicit-any */
type AnyDoc = Record<string, any>;

function toObjectIdOrNull(id: string): Types.ObjectId | null {
  return Types.ObjectId.isValid(id) ? new Types.ObjectId(id) : null;
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
// Access gating — ports of the reaction_service private helpers.
// ---------------------------------------------------------------------------

/** Port of `_get_author_room_or_404`: invalid id → 400, missing → 404. */
async function getAuthorRoomOr404(authorRoomId: string): Promise<AnyDoc> {
  const oid = toObjectIdOrNull(authorRoomId);
  if (oid === null) throw new HttpError(400, "Invalid author_room ID format");
  const room = await AuthorRoom.findById(oid).lean<AnyDoc>();
  if (!room) throw new HttpError(404, "AuthorRoom not found");
  return room;
}

/**
 * Port of `_get_member_user_or_401`: an invalid ObjectId userId OR a missing
 * user both raise 401 "Invalid token" (legacy raises 401, not 400, here).
 */
async function getMemberUserOr401(userId: string): Promise<UserDoc> {
  if (!Types.ObjectId.isValid(userId)) throw new HttpError(401, "Invalid token");
  const user = await User.findById(userId).lean<UserDoc>();
  if (!user) throw new HttpError(401, "Invalid token");
  return user;
}

/**
 * Port of `_ensure_reaction_access`: room (404) → its chapter (404 "Chapter not
 * found") → member (401) → `hasChapterAccess` (403). Chapter is looked up by
 * `_id` (the room's `chapterId`); an invalid id behaves like "not found".
 */
async function ensureReactionAccess(userId: string, authorRoomId: string): Promise<void> {
  const room = await getAuthorRoomOr404(authorRoomId);

  const chapterOid = room.chapterId ? toObjectIdOrNull(String(room.chapterId)) : null;
  const chapter = chapterOid ? await Chapter.findById(chapterOid).lean<ChapterDoc>() : null;
  if (!chapter) throw new HttpError(404, "Chapter not found");

  const user = await getMemberUserOr401(userId);

  const canAccess = await hasChapterAccess(user, chapter);
  if (!canAccess) {
    throw new HttpError(403, "You do not have access to react to this chapter");
  }
}

// ---------------------------------------------------------------------------
// CREATE — port of `add_reaction`.
// ---------------------------------------------------------------------------

/**
 * Create the caller's reaction in an author room. Ensures access first; if the
 * caller already reacted, the existing reaction is REPLACED (legacy updates in
 * place rather than 409). A racing insert on the unique index surfaces as 409.
 */
export async function addReaction(input: {
  reaction: string;
  authorRoomId: string;
  userId: string;
}): Promise<ReactionOut> {
  await db();
  await ensureReactionAccess(input.userId, input.authorRoomId);

  const existing = await Reaction.findOne({
    userId: input.userId,
    authorRoomId: input.authorRoomId,
  }).lean<ReactionDoc>();

  if (existing) {
    const eid = existing._id ? String(existing._id) : "";
    const oid = toObjectIdOrNull(eid);
    if (oid === null) throw new HttpError(400, "Invalid reaction ID format");
    const updated = await Reaction.findOneAndUpdate(
      { _id: oid },
      { $set: { reaction: input.reaction, last_updated: Math.floor(Date.now() / 1000) } },
      { new: true },
    ).lean<ReactionDoc>();
    if (!updated) throw new HttpError(404, "Reaction not found or update failed");
    return toReactionOut(updated);
  }

  const now = Math.floor(Date.now() / 1000);
  try {
    const created = await Reaction.create({
      reaction: input.reaction,
      authorRoomId: input.authorRoomId,
      userId: input.userId,
      date_created: now,
      last_updated: now,
    });
    const doc = (created.toObject ? created.toObject() : created) as ReactionDoc;
    return toReactionOut(doc);
  } catch (err) {
    if (isDuplicateKeyError(err)) {
      throw new HttpError(409, "You have already reacted to this author room");
    }
    throw err;
  }
}

// ---------------------------------------------------------------------------
// GET caller's reaction — port of `retrieve_reaction_by_user_and_room`.
// ---------------------------------------------------------------------------

/** The caller's reaction for a room; 404 when absent. No access gate (legacy). */
export async function retrieveReactionByUserAndRoom(
  userId: string,
  authorRoomId: string,
): Promise<ReactionOut> {
  await db();
  const doc = await Reaction.findOne({ userId, authorRoomId }).lean<ReactionDoc>();
  if (!doc) throw new HttpError(404, "Reaction not found for user in this room");
  return toReactionOut(doc);
}

// ---------------------------------------------------------------------------
// LIST + count — ports of `retrieve_reactions` / `retrieve_reactions_count`.
// ---------------------------------------------------------------------------

/** All reactions, paginated (public list; no filter). */
export async function retrieveReactions(skip = 0, limit = 20): Promise<ReactionOut[]> {
  await db();
  const docs = await Reaction.find({}).skip(skip).limit(limit).lean<ReactionDoc[]>();
  return docs.map((doc) => toReactionOut(doc));
}

/** Total count of ALL reactions (no filter). */
export async function retrieveReactionsCount(): Promise<number> {
  await db();
  return Reaction.countDocuments({});
}

// ---------------------------------------------------------------------------
// UPDATE — port of `update_reaction_by_id`.
// ---------------------------------------------------------------------------

/**
 * Update the caller's reaction in a room. `reaction` is required (400 when
 * null/absent); ensures access; existing (404); updates by `_id` (404 on
 * failure). `last_updated` is auto-refreshed.
 */
export async function updateReactionByUserAndRoom(
  userId: string,
  authorRoomId: string,
  data: { reaction?: string | null },
): Promise<ReactionOut> {
  if (data.reaction === null || data.reaction === undefined) {
    throw new HttpError(400, "reaction is required");
  }

  await db();
  await ensureReactionAccess(userId, authorRoomId);

  const existing = await Reaction.findOne({ userId, authorRoomId }).lean<ReactionDoc>();
  if (!existing) throw new HttpError(404, "Reaction not found for user in this room");

  const eid = existing._id ? String(existing._id) : "";
  const oid = toObjectIdOrNull(eid);
  if (oid === null) throw new HttpError(400, "Invalid reaction ID format");

  const updated = await Reaction.findOneAndUpdate(
    { _id: oid },
    { $set: { reaction: data.reaction, last_updated: Math.floor(Date.now() / 1000) } },
    { new: true },
  ).lean<ReactionDoc>();
  if (!updated) throw new HttpError(404, "Reaction not found or update failed");
  return toReactionOut(updated);
}

// ---------------------------------------------------------------------------
// DELETE — port of `remove_reaction_for_user`.
// ---------------------------------------------------------------------------

/**
 * Delete the caller's reaction in a room. Ensures access; existing (404);
 * deletes by `_id` (404 if nothing removed). Returns true on success.
 */
export async function removeReactionForUser(
  userId: string,
  authorRoomId: string,
): Promise<boolean> {
  await db();
  await ensureReactionAccess(userId, authorRoomId);

  const existing = await Reaction.findOne({ userId, authorRoomId }).lean<ReactionDoc>();
  if (!existing) throw new HttpError(404, "Reaction not found for user in this room");

  const eid = existing._id ? String(existing._id) : "";
  const oid = toObjectIdOrNull(eid);
  if (oid === null) throw new HttpError(400, "Invalid reaction ID format");

  const result = await Reaction.deleteOne({ _id: oid });
  if ((result.deletedCount ?? 0) === 0) throw new HttpError(404, "Reaction not found");
  return true;
}
