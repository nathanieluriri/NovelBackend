/**
 * Admin user-management helpers — port of the admin-facing user functions in
 * `../services/admin_services.py` (`get_all_user_details`, `get_one_user_details`,
 * `update_user_details`) plus the `read` lookup in
 * `../repositories/read_repo.py` (`get_particular_chapter_user_has_read`).
 *
 * Consumed by the admin user routes:
 *   GET   /api/v2/user/all/user-details
 *   GET   /api/v2/user/{userId}/user-details
 *   PATCH /api/v2/user/{userId}/status/{new_status}
 *
 * Faithful-port notes (legacy quirks kept on purpose — "match, then refactor"):
 *  - `get_all_users()` is called with `limit=None` → returns EVERY user (no
 *    pagination); each becomes a `UserOut` with null tokens / empty
 *    bookmarks+likes (excluded later by the route's exclude_none envelope).
 *  - `get_one_user_details` walks `user.unlockedChapters`, loads each chapter,
 *    and joins a per-chapter `hasRead` flag from the `read` collection
 *    (default `false` when no row exists). Bookmarks/likes are NOT loaded here
 *    (legacy leaves them as `[]`).
 *  - `update_user_details` does `$set` of the FULL `UserUpdate` dump — i.e.
 *    `{firstName:null, lastName:null, avatar:null, status:<new>}`. The legacy
 *    `model_dump()` (no exclude_none) blanks firstName/lastName/avatar. We
 *    reproduce that exactly. `find_one_and_update` returns the AFTER doc.
 */
import { db } from "@/lib/db";
import { Chapter, ReadRecord, User, type UserDoc } from "@/lib/models";
import {
  toChapterSyncVersion,
  toUserOut,
  type ChapterOutSyncVersion,
  type UserOut,
  type UserOutChapterDetails,
  type UserStatus,
} from "@/lib/serializers";

const OBJECT_ID_RE = /^[a-f\d]{24}$/i;

/** Whether the user has a `read` row marking `chapterId` as read (default false). */
async function hasReadChapter(userId: string, chapterId: string): Promise<boolean> {
  const row = await ReadRecord.findOne({ userId, chapterId })
    .select({ hasRead: 1 })
    .lean<{ hasRead?: boolean } | null>();
  return Boolean(row?.hasRead);
}

/**
 * `get_all_user_details` — every user as a bare `UserOut` (no tokens / activity).
 * Returns a flat array; the route envelopes it as `data: [...]`.
 */
export async function getAllUserDetails(): Promise<UserOut[]> {
  await db();
  const users = await User.find({}).lean<UserDoc[]>();
  return users.map((user) => toUserOut(user));
}

/**
 * `get_one_user_details` — `UserOutChapterDetails`: the user joined with the
 * full chapter docs for each unlocked chapter, each carrying a `hasRead` flag.
 * Returns null when the user does not exist (route → 404).
 */
export async function getOneUserDetails(userId: string): Promise<UserOutChapterDetails | null> {
  await db();
  if (!OBJECT_ID_RE.test(userId)) return null;
  const user = await User.findById(userId).lean<UserDoc>();
  if (!user) return null;

  const unlockedChapters: unknown = user.unlockedChapters;
  const chapterDetails: ChapterOutSyncVersion[] = [];
  if (Array.isArray(unlockedChapters)) {
    const realUserId = String(user._id);
    for (const rawChapterId of unlockedChapters) {
      const chapterId = String(rawChapterId);
      if (!OBJECT_ID_RE.test(chapterId)) continue;
      const chapter = await Chapter.findById(chapterId).lean<Record<string, unknown>>();
      if (!chapter) continue;
      const hasRead = await hasReadChapter(realUserId, chapterId);
      chapterDetails.push(toChapterSyncVersion(chapter, hasRead));
    }
  }

  return toUserOut(user, { chapterDetails });
}

/**
 * `update_user_details` — `$set` the FULL UserUpdate dump (firstName/lastName/
 * avatar blanked to null, plus the new status), returning the updated `UserOut`.
 * Returns null when the user is missing (route → 404).
 */
export async function updateUserStatus(
  userId: string,
  newStatus: UserStatus,
): Promise<UserOut | null> {
  await db();
  if (!OBJECT_ID_RE.test(userId)) return null;
  const updated = await User.findByIdAndUpdate(
    userId,
    { $set: { firstName: null, lastName: null, avatar: null, status: newStatus } },
    { new: true },
  ).lean<UserDoc>();
  if (!updated) return null;
  return toUserOut(updated);
}
