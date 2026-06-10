/**
 * Chapter service — port of `services/chapter_services.py` (+ repos
 * `chapter_repo.py`, `page_repo.py`, `book_repo.py`). One concern: chapter
 * CRUD + hydration. HTTP shaping (envelope/pagination) lives in the routes.
 *
 * Behavioral notes carried over from legacy:
 *  - create: number = (#existing chapters)+1; then recompute the parent book's
 *    `chapterCount` and `chapters` array from the DB. (Legacy's first-chapter
 *    branch wrote the int `chapters=1`; per the task we recompute the array in
 *    all cases — chapterCount and a real id array.)
 *  - delete: cascade-delete pages (BOTH the modern `chapterId` key AND the
 *    legacy snake `chapter_id` key some old docs carry), shift the `number` of
 *    later chapters down by one, recompute the book; return the pre-delete doc.
 *  - update: legacy `status`→`accessType` mapping (premium/locked → paid) and
 *    the unlockBundleId bundle rules (paid requires it; free/subscription must
 *    NOT set it) — 422 on rule violation, matching the legacy Pydantic raise.
 *  - hydrateChapterOut: recompute pageCount/pages from the pages collection,
 *    commentsCount (OR of modern {targetType:"chapter",targetId} and legacy
 *    {chapterId}) and likesCount from their collections — never from stored
 *    counters.
 */
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { nowIso } from "@/lib/util/dates";
import { Book, Chapter, Comment, Like, Page } from "@/lib/models";
import type { ChapterDoc } from "@/lib/models";
import { toChapterOut, type ChapterOut } from "@/lib/serializers";

/* eslint-disable @typescript-eslint/no-explicit-any */
type AnyDoc = Record<string, any>;

const OBJECT_ID_RE = /^[a-fA-F0-9]{24}$/;

/** Mirrors LEGACY_STATUS_TO_ACCESS in `schemas/chapter_schema.py`. */
const LEGACY_STATUS_TO_ACCESS: Record<string, "free" | "subscription" | "paid"> = {
  free: "free",
  subscription: "subscription",
  paid: "paid",
  premium: "paid",
  locked: "paid",
};

// ---------------------------------------------------------------------------
// Hydration — recompute pageCount/pages/commentsCount/likesCount from the DB.
// ---------------------------------------------------------------------------

interface ChapterCounts {
  pageCount: number;
  pages: string[];
  commentsCount: number;
  likesCount: number;
}

async function computeChapterCounts(chapterId: string): Promise<ChapterCounts> {
  const [pageDocs, commentsCount, likesCount] = await Promise.all([
    Page.find({ chapterId }, { _id: 1 }).lean<AnyDoc[]>(),
    Comment.countDocuments({
      $or: [{ targetType: "chapter", targetId: chapterId }, { chapterId }],
    }),
    Like.countDocuments({ chapterId }),
  ]);
  const pages = (pageDocs ?? []).map((p) => String(p._id));
  return {
    pageCount: pages.length,
    pages,
    commentsCount,
    likesCount,
  };
}

/**
 * Build a fully hydrated ChapterOut from a raw chapter doc — recomputing
 * pageCount/pages/commentsCount/likesCount from their collections (mirrors the
 * legacy `ChapterOut.set_counts` async validator).
 */
export async function hydrateChapterOut(chapter: ChapterDoc): Promise<ChapterOut> {
  await db();
  const id = String(chapter?._id ?? chapter?.id ?? "");
  const counts = await computeChapterCounts(id);
  return toChapterOut(chapter, counts);
}

async function hydrateMany(chapters: ChapterDoc[]): Promise<ChapterOut[]> {
  return Promise.all(chapters.map((c) => hydrateChapterOut(c)));
}

// ---------------------------------------------------------------------------
// Parent-book recompute (chapterCount + chapters id array) from the DB.
// ---------------------------------------------------------------------------

async function recomputeBook(bookId: string): Promise<void> {
  if (!bookId || !OBJECT_ID_RE.test(bookId)) return;
  const chapters = await Chapter.find({ bookId }, { _id: 1 }).lean<AnyDoc[]>();
  const ids = (chapters ?? []).map((c) => String(c._id));
  await Book.updateOne(
    { _id: bookId },
    { $set: { chapterCount: ids.length, chapters: ids, dateUpdated: nowIso() } },
  );
}

// ---------------------------------------------------------------------------
// Read paths.
// ---------------------------------------------------------------------------

/** Paginated chapters for a book (admin + user list variants share this). */
export async function listChapters(
  bookId: string,
  skip: number,
  limit: number,
): Promise<ChapterOut[]> {
  await db();
  if (!OBJECT_ID_RE.test(bookId)) {
    // Legacy repo raised a 500 "Invalid Book Id"; preserve that behavior.
    throw new HttpError(500, "Invalid Book Id");
  }
  // Legacy `get_chapter_by_bookId` issues no explicit sort — natural order.
  const chapters = await Chapter.find({ bookId })
    .skip(skip)
    .limit(limit)
    .lean<ChapterDoc[]>();
  return hydrateMany(chapters ?? []);
}

/** Total chapter count for a book (list `total`). */
export async function countChapters(bookId: string): Promise<number> {
  await db();
  return Chapter.countDocuments({ bookId });
}

/** Single chapter by id → 404 when missing (legacy `fetch_chapter_with_chapterId`). */
export async function getChapterById(chapterId: string): Promise<ChapterOut> {
  await db();
  const chapter = OBJECT_ID_RE.test(chapterId)
    ? await Chapter.findById(chapterId).lean<ChapterDoc>()
    : null;
  if (!chapter) throw new HttpError(404, "Chapter not found");
  return hydrateChapterOut(chapter);
}

/** Single chapter by (bookId, number) → 404 when missing. */
export async function getChapterByNumber(
  bookId: string,
  chapterNumber: number,
): Promise<ChapterOut> {
  await db();
  const chapter = OBJECT_ID_RE.test(bookId)
    ? await Chapter.findOne({ bookId, number: chapterNumber }).lean<ChapterDoc>()
    : null;
  if (!chapter) throw new HttpError(404, "Chapter not found");
  return hydrateChapterOut(chapter);
}

// ---------------------------------------------------------------------------
// Create.
// ---------------------------------------------------------------------------

export interface ChapterCreateInput {
  bookId: string;
  chapterLabel: string;
  status?: string | null;
  accessType: "free" | "subscription" | "paid";
  unlockBundleId?: string | null;
  coverImage?: string | null;
}

/**
 * Create a chapter, then recompute the parent book's chapterCount + chapters
 * array. New chapter `number` = (#existing chapters for the book) + 1.
 */
export async function createChapter(input: ChapterCreateInput): Promise<ChapterOut> {
  await db();
  const now = nowIso();
  const existingCount = await Chapter.countDocuments({ bookId: input.bookId });
  const created = await Chapter.create({
    bookId: input.bookId,
    chapterLabel: input.chapterLabel,
    status: input.status ?? null,
    accessType: input.accessType,
    unlockBundleId: input.unlockBundleId ?? null,
    coverImage: input.coverImage ?? null,
    number: existingCount + 1,
    dateCreated: now,
    dateUpdated: now,
    pageCount: 0,
    pages: null,
  });
  const doc = created.toObject() as ChapterDoc;
  await recomputeBook(String(input.bookId));
  return hydrateChapterOut(doc);
}

// ---------------------------------------------------------------------------
// Delete.
// ---------------------------------------------------------------------------

/**
 * Delete a chapter: cascade-delete its pages (modern `chapterId` AND legacy
 * snake `chapter_id` keys), shift later chapters' `number` down by one,
 * recompute the parent book, and return the deleted chapter (pre-delete state)
 * as a ChapterOut. 404 when the chapter does not exist.
 */
export async function deleteChapter(chapterId: string): Promise<ChapterOut> {
  await db();
  const chapter = OBJECT_ID_RE.test(chapterId)
    ? await Chapter.findById(chapterId).lean<ChapterDoc>()
    : null;
  if (!chapter) throw new HttpError(404, "Chapter not found");

  // Cascade: legacy deleted by the snake `chapter_id` key only; we also clear
  // the modern `chapterId` key so no orphan pages remain.
  await Page.deleteMany({ $or: [{ chapterId }, { chapter_id: chapterId }] });

  await Chapter.deleteOne({ _id: chapterId });

  // Shift the `number` of all later chapters down by one.
  const deletedPosition = Number(chapter.number ?? 0);
  const bookId = String(chapter.bookId ?? "");
  await Chapter.updateMany(
    { bookId, number: { $gt: deletedPosition } },
    { $inc: { number: -1 } },
  );

  await recomputeBook(bookId);

  // Legacy returns the find_one_and_delete result (pre-delete doc).
  return hydrateChapterOut(chapter);
}

// ---------------------------------------------------------------------------
// Update (status / label / accessType / unlockBundleId / coverImage).
// ---------------------------------------------------------------------------

export interface ChapterUpdateInput {
  chapterLabel?: string | null;
  status?: string | null;
  accessType?: "free" | "subscription" | "paid" | null;
  unlockBundleId?: string | null;
  coverImage?: string | null;
}

/**
 * Resolve the effective accessType for an update payload using the same legacy
 * rules as `ChapterUpdateStatusOrLabel.normalize_access_values`: if accessType
 * is absent but `status` is present, map status (premium/locked → paid; unknown
 * → free). If neither is present, accessType stays undefined (unchanged).
 */
function normalizeUpdateAccess(input: ChapterUpdateInput): "free" | "subscription" | "paid" | undefined {
  if (input.accessType) return input.accessType;
  if (input.status !== null && input.status !== undefined) {
    const mapped = LEGACY_STATUS_TO_ACCESS[String(input.status).trim().toLowerCase()];
    return mapped ?? "free";
  }
  return undefined;
}

/**
 * Validate the unlockBundleId bundle rules against the resolved accessType,
 * mirroring `validate_bundle_rules` (422 — legacy Pydantic ValueError surfaces
 * as a validation error):
 *  - accessType "paid"          requires unlockBundleId
 *  - "free" / "subscription"    must NOT have unlockBundleId
 */
function validateBundleRules(
  accessType: "free" | "subscription" | "paid" | undefined,
  unlockBundleId: string | null | undefined,
): void {
  if (accessType === undefined) return;
  if (accessType === "paid" && !unlockBundleId) {
    throw new HttpError(422, "Validation failed", [
      {
        type: "value_error",
        loc: ["body"],
        msg: "Value error, unlockBundleId is required when accessType is paid",
        input: null,
      },
    ]);
  }
  if (
    (accessType === "free" || accessType === "subscription") &&
    unlockBundleId !== null &&
    unlockBundleId !== undefined
  ) {
    throw new HttpError(422, "Validation failed", [
      {
        type: "value_error",
        loc: ["body"],
        msg: "Value error, unlockBundleId must be empty unless accessType is paid",
        input: null,
      },
    ]);
  }
}

/**
 * Apply a status/label update. Only non-null fields are written (legacy
 * `model_dump(exclude_none=True)`); `dateUpdated` is always refreshed. 404 when
 * the chapter does not exist after the write.
 */
export async function updateChapter(
  chapterId: string,
  input: ChapterUpdateInput,
): Promise<ChapterOut> {
  await db();

  const accessType = normalizeUpdateAccess(input);
  validateBundleRules(accessType, input.unlockBundleId);

  const set: AnyDoc = { dateUpdated: nowIso() };
  if (input.chapterLabel !== null && input.chapterLabel !== undefined) set.chapterLabel = input.chapterLabel;
  if (input.status !== null && input.status !== undefined) set.status = input.status;
  if (accessType !== undefined) set.accessType = accessType;
  if (input.unlockBundleId !== null && input.unlockBundleId !== undefined) {
    set.unlockBundleId = input.unlockBundleId;
  }
  if (input.coverImage !== null && input.coverImage !== undefined) set.coverImage = input.coverImage;

  if (OBJECT_ID_RE.test(chapterId)) {
    await Chapter.updateOne({ _id: chapterId }, { $set: set });
  }

  const updated = OBJECT_ID_RE.test(chapterId)
    ? await Chapter.findById(chapterId).lean<ChapterDoc>()
    : null;
  if (!updated) throw new HttpError(404, "Chapter not found");
  return hydrateChapterOut(updated);
}
