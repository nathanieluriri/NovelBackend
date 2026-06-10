/**
 * Author-room service — port of `services/author_room_service.py`
 * (+ `repositories/author_room.py`) for the v2 `/api/v2/author_room/*` surface.
 *
 * This is a v2-only resource (no v1 equivalent). Dates are stored as EPOCH
 * SECONDS (`date_created`/`last_updated`); the serializer (`toAuthorRoomOut`)
 * maps them to ISO `dateCreated`/`lastUpdated` `+00:00` strings (schema.md §0.4).
 *
 * Behavioural parity notes (reproduced EXACTLY — do not "fix"):
 *  - CREATE (`add_author_room`): insert → hydrate `chapterSummary` (cache seam)
 *    → hydrate `reactionSummary` (single aggregate over `reactions`). No
 *    `userReaction` on create (legacy leaves it null).
 *  - GET by id (`retrieve_author_room_by_author_room_id`): invalid ObjectId →
 *    400 "Invalid author_room ID format"; missing → 404 "AuthorRoom not found";
 *    else hydrate `chapterSummary` + `reactionSummary` + `userReaction` (the
 *    caller's reaction string, or null).
 *  - LIST (`retrieve_author_rooms`): paginated; `chapterSummary` hydrated
 *    per-item (cache-aside), but `reactionSummary` and `userReaction` are
 *    BATCHED by the room-id set (one aggregate + one `$in` query) — NO N+1.
 *  - UPDATE (`update_author_room_by_id`): invalid id → 400; missing/update
 *    failed → 404; else hydrate `chapterSummary` + `reactionSummary` (no
 *    `userReaction`, matching legacy).
 *  - DELETE (`remove_author_room`): invalid id → 400; nothing deleted → 404;
 *    else returns true.
 *  - COUNT (`retrieve_author_rooms_count`): total of ALL author rooms (no filter).
 *
 * Models (AuthorRoom, Reaction) are imported DIRECTLY (CONVENTIONS.md: no
 * cross-service imports). `getChapterSummary` is consumed from the cache seam.
 */
import { Types } from "mongoose";

import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { getChapterSummary } from "@/lib/cache/summary";
import { AuthorRoom, Reaction, type AuthorRoomDoc } from "@/lib/models";
import {
  toAuthorRoomOut,
  type AuthorRoomOut,
  type AuthorRoomOutExtras,
} from "@/lib/serializers";

/* eslint-disable @typescript-eslint/no-explicit-any */
type AnyDoc = Record<string, any>;

function toObjectIdOrNull(id: string): Types.ObjectId | null {
  return Types.ObjectId.isValid(id) ? new Types.ObjectId(id) : null;
}

// ---------------------------------------------------------------------------
// Reaction hydration helpers (single-item) — ports of
// `get_reaction_summary_by_author_room_id` / `get_reaction_by_user_and_room`.
// ---------------------------------------------------------------------------

/**
 * Aggregate reaction counts for ONE author room: `$group` by reaction value,
 * skipping non-string / empty reactions and null group keys. Returns
 * `{ <reaction>: <count> }` (default `{}`).
 */
async function reactionSummaryForRoom(authorRoomId: string): Promise<Record<string, number>> {
  if (!authorRoomId) return {};
  const rows = await Reaction.aggregate<{ _id: unknown; count: number }>([
    { $match: { authorRoomId } },
    { $match: { reaction: { $type: "string", $ne: "" } } },
    { $group: { _id: "$reaction", count: { $sum: 1 } } },
  ]);
  const out: Record<string, number> = {};
  for (const row of rows) {
    if (row._id === null || row._id === undefined) continue;
    out[String(row._id)] = Number(row.count ?? 0);
  }
  return out;
}

/** The caller's reaction STRING for one room (or null), if `userId` is given. */
async function userReactionForRoom(
  authorRoomId: string,
  userId?: string | null,
): Promise<string | null> {
  if (!userId || !authorRoomId) return null;
  const reaction = await Reaction.findOne({ userId, authorRoomId }).lean<AnyDoc>();
  if (!reaction) return null;
  const value = reaction.reaction;
  return value === null || value === undefined ? null : String(value);
}

/** chapterSummary for a room (cache-aside) when the room has a chapterId. */
async function chapterSummaryForRoom(chapterId: unknown): Promise<AuthorRoomOutExtras["chapterSummary"]> {
  const id = chapterId ? String(chapterId) : "";
  if (!id) return null;
  return getChapterSummary(id);
}

// ---------------------------------------------------------------------------
// Batched reaction hydration (list) — ports of
// `get_reaction_summaries_for_author_room_ids` /
// `get_reactions_by_user_for_author_room_ids`.
// ---------------------------------------------------------------------------

/** One aggregate over the whole room-id set → `{ roomId: { reaction: count } }`. */
async function reactionSummariesForRooms(
  authorRoomIds: string[],
): Promise<Map<string, Record<string, number>>> {
  const map = new Map<string, Record<string, number>>();
  if (authorRoomIds.length === 0) return map;
  const rows = await Reaction.aggregate<{
    _id: { authorRoomId?: unknown; reaction?: unknown };
    count: number;
  }>([
    { $match: { authorRoomId: { $in: authorRoomIds } } },
    { $match: { reaction: { $type: "string", $ne: "" } } },
    {
      $group: {
        _id: { authorRoomId: "$authorRoomId", reaction: "$reaction" },
        count: { $sum: 1 },
      },
    },
  ]);
  for (const row of rows) {
    const key = row._id ?? {};
    const roomId = key.authorRoomId;
    const reaction = key.reaction;
    if (roomId === null || roomId === undefined || reaction === null || reaction === undefined) {
      continue;
    }
    const roomKey = String(roomId);
    const existing = map.get(roomKey) ?? {};
    existing[String(reaction)] = Number(row.count ?? 0);
    map.set(roomKey, existing);
  }
  return map;
}

/** One `$in` query → `{ roomId: <caller's reaction string> }` for the room-id set. */
async function userReactionsForRooms(
  authorRoomIds: string[],
  userId?: string | null,
): Promise<Map<string, string>> {
  const map = new Map<string, string>();
  if (!userId || authorRoomIds.length === 0) return map;
  const docs = await Reaction.find({
    userId,
    authorRoomId: { $in: authorRoomIds },
  }).lean<AnyDoc[]>();
  for (const doc of docs) {
    if (doc.authorRoomId === null || doc.authorRoomId === undefined) continue;
    const value = doc.reaction;
    if (value === null || value === undefined) continue;
    map.set(String(doc.authorRoomId), String(value));
  }
  return map;
}

// ---------------------------------------------------------------------------
// CREATE — port of `add_author_room`.
// ---------------------------------------------------------------------------

/**
 * Create an author-room entry, then hydrate chapterSummary + reactionSummary
 * (a freshly created room has no reactions yet → `{}`). userReaction stays null.
 */
export async function addAuthorRoom(input: { text: string; chapterId: string }): Promise<AuthorRoomOut> {
  await db();
  const now = Math.floor(Date.now() / 1000);
  const created = await AuthorRoom.create({
    text: input.text,
    chapterId: input.chapterId,
    date_created: now,
    last_updated: now,
  });
  const doc = (created.toObject ? created.toObject() : created) as AuthorRoomDoc;

  const id = doc._id ? String(doc._id) : "";
  const [chapterSummary, reactionSummary] = await Promise.all([
    chapterSummaryForRoom(doc.chapterId),
    id ? reactionSummaryForRoom(id) : Promise.resolve<Record<string, number>>({}),
  ]);
  return toAuthorRoomOut(doc, { chapterSummary, reactionSummary });
}

// ---------------------------------------------------------------------------
// GET by id — port of `retrieve_author_room_by_author_room_id`.
// ---------------------------------------------------------------------------

/**
 * Fetch one author room (invalid id → 400, missing → 404), hydrated with
 * chapterSummary + reactionSummary + the caller's userReaction.
 */
export async function retrieveAuthorRoomById(
  id: string,
  userId?: string | null,
): Promise<AuthorRoomOut> {
  const oid = toObjectIdOrNull(id);
  if (oid === null) throw new HttpError(400, "Invalid author_room ID format");

  await db();
  const doc = await AuthorRoom.findById(oid).lean<AuthorRoomDoc>();
  if (!doc) throw new HttpError(404, "AuthorRoom not found");

  const roomId = doc._id ? String(doc._id) : "";
  const [chapterSummary, reactionSummary, userReaction] = await Promise.all([
    chapterSummaryForRoom(doc.chapterId),
    roomId ? reactionSummaryForRoom(roomId) : Promise.resolve<Record<string, number>>({}),
    roomId ? userReactionForRoom(roomId, userId) : Promise.resolve<string | null>(null),
  ]);
  return toAuthorRoomOut(doc, { chapterSummary, reactionSummary, userReaction });
}

// ---------------------------------------------------------------------------
// LIST + count — ports of `retrieve_author_rooms` / `retrieve_author_rooms_count`.
// ---------------------------------------------------------------------------

/**
 * Paginated author rooms. `chapterSummary` is hydrated per-item (cache-aside);
 * `reactionSummary` + `userReaction` are BATCHED by the room-id set (one
 * aggregate + one `$in` query) to avoid an N+1.
 */
export async function retrieveAuthorRooms(
  skip = 0,
  limit = 20,
  userId?: string | null,
): Promise<AuthorRoomOut[]> {
  await db();
  const docs = await AuthorRoom.find({}).skip(skip).limit(limit).lean<AuthorRoomDoc[]>();
  if (docs.length === 0) return [];

  const roomIds = docs.map((d) => (d._id ? String(d._id) : "")).filter((rid) => rid);
  const [summaryMap, reactionMap] = await Promise.all([
    reactionSummariesForRooms(roomIds),
    userReactionsForRooms(roomIds, userId),
  ]);

  const out: AuthorRoomOut[] = [];
  for (const doc of docs) {
    const roomId = doc._id ? String(doc._id) : "";
    const chapterSummary = await chapterSummaryForRoom(doc.chapterId);
    out.push(
      toAuthorRoomOut(doc, {
        chapterSummary,
        reactionSummary: roomId ? summaryMap.get(roomId) ?? {} : {},
        userReaction: roomId ? userReactionMap(reactionMap, roomId) : null,
      }),
    );
  }
  return out;
}

function userReactionMap(map: Map<string, string>, roomId: string): string | null {
  return map.has(roomId) ? (map.get(roomId) as string) : null;
}

/** Total count of ALL author rooms (no filter), per legacy `count_author_rooms`. */
export async function retrieveAuthorRoomsCount(): Promise<number> {
  await db();
  return AuthorRoom.countDocuments({});
}

// ---------------------------------------------------------------------------
// UPDATE — port of `update_author_room_by_id`.
// ---------------------------------------------------------------------------

/**
 * Update an author room's text (invalid id → 400, missing/update failed → 404).
 * `last_updated` is refreshed to the current epoch (legacy auto field). The
 * result hydrates chapterSummary + reactionSummary (no userReaction).
 */
export async function updateAuthorRoomById(
  id: string,
  data: { text: string },
): Promise<AuthorRoomOut> {
  const oid = toObjectIdOrNull(id);
  if (oid === null) throw new HttpError(400, "Invalid author_room ID format");

  await db();
  const updated = await AuthorRoom.findOneAndUpdate(
    { _id: oid },
    { $set: { text: data.text, last_updated: Math.floor(Date.now() / 1000) } },
    { new: true },
  ).lean<AuthorRoomDoc>();
  if (!updated) throw new HttpError(404, "AuthorRoom not found or update failed");

  const roomId = updated._id ? String(updated._id) : "";
  const [chapterSummary, reactionSummary] = await Promise.all([
    chapterSummaryForRoom(updated.chapterId),
    roomId ? reactionSummaryForRoom(roomId) : Promise.resolve<Record<string, number>>({}),
  ]);
  return toAuthorRoomOut(updated, { chapterSummary, reactionSummary });
}

// ---------------------------------------------------------------------------
// DELETE — port of `remove_author_room`.
// ---------------------------------------------------------------------------

/**
 * Delete an author room by id (invalid id → 400, nothing deleted → 404).
 * Returns true on success — the route serializes that to `{deleted:true}`.
 */
export async function removeAuthorRoom(id: string): Promise<boolean> {
  const oid = toObjectIdOrNull(id);
  if (oid === null) throw new HttpError(400, "Invalid author_room ID format");

  await db();
  const result = await AuthorRoom.deleteOne({ _id: oid });
  if ((result.deletedCount ?? 0) === 0) throw new HttpError(404, "AuthorRoom not found");
  return true;
}
