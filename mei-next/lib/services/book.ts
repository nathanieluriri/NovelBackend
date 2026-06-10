/**
 * Book service — port of `services/book_services.py` + `repositories/book_repo.py`.
 *
 * Books own an ordered `number` (1-based position). Creating appends to the end
 * (`number = count + 1`); deleting cascades to the book's chapters and their
 * pages, then closes the gap by shifting every later book's `number` down by 1
 * (legacy `update_book_order_after_delete`).
 *
 * All book/chapter/page cache invalidation is performed by the ROUTES (per the
 * caching.md bust table) — the service only touches Mongo.
 */
import { Types } from "mongoose";
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { nowIso } from "@/lib/util/dates";
import { Book, Chapter, Page, type BookDoc } from "@/lib/models";

/** Legacy `maybe_id` semantics: a non-ObjectId id behaves like "not found". */
function isValidObjectId(id: string): boolean {
  return Types.ObjectId.isValid(id) && String(new Types.ObjectId(id)) === id;
}

/** Input shape for {@link updateBook} — mirrors legacy `BookUpdate`. */
export interface BookUpdateInput {
  name?: string | null;
  number?: number | null;
  chapterCount?: number | null;
  chapters?: string[] | null;
}

/** Total book count (legacy `count_all_books`). */
export async function countBooks(): Promise<number> {
  await db();
  return Book.countDocuments({});
}

/**
 * List books with skip/limit (legacy `get_all_books_paginated`).
 * Natural insertion order — legacy issues no explicit sort.
 */
export async function listBooks(skip = 0, limit = 20): Promise<BookDoc[]> {
  await db();
  return Book.find({}).skip(skip).limit(limit).lean<BookDoc[]>();
}

/**
 * Create a book (legacy `add_book`).
 *
 * The legacy flow computes the next position as `len(all_books) + 1` and, in
 * practice, always inserts with the supplied `name` unchanged (the rename
 * branches keyed on `number==0` are dead — freshly created books all have
 * `number >= 1`). We reproduce the observable result: append at the end with
 * `number = count + 1`, `dateCreated`/`dateUpdated = now`.
 */
export async function createBook(name: string): Promise<BookDoc> {
  await db();
  const count = await Book.countDocuments({});
  const now = nowIso();
  const created = await Book.create({
    name,
    number: count + 1,
    dateCreated: now,
    dateUpdated: now,
    chapterCount: 0,
    chapters: null,
  });
  return created.toObject() as BookDoc;
}

/**
 * Delete a book and cascade (legacy `delete_book`):
 *  1. delete all chapters with this `bookId`,
 *  2. delete all pages whose `chapterId` is in the book's `chapters` array,
 *  3. delete the book itself,
 *  4. shift every book positioned after it (`number > deleted`) down by 1.
 *
 * Returns the deleted book doc. Legacy raised a 400 when the id resolved to no
 * book (its `BookOut(**None)` blew up inside the route try/except) — we mirror
 * that with a 400.
 */
export async function deleteBook(bookId: string): Promise<BookDoc> {
  await db();
  const book = isValidObjectId(bookId) ? await Book.findById(bookId).lean<BookDoc>() : null;
  if (!book) {
    throw new HttpError(400, "Book not found");
  }

  await Chapter.deleteMany({ bookId });

  const chapters = book.chapters;
  if (Array.isArray(chapters) && chapters.length > 0) {
    await Page.deleteMany({ chapterId: { $in: chapters } });
  }

  await Book.deleteOne({ _id: book._id });

  const deletedPosition = book.number;
  if (typeof deletedPosition === "number") {
    await Book.updateMany({ number: { $gt: deletedPosition } }, { $inc: { number: -1 } });
  }

  return book;
}

/**
 * Update a book (legacy `change_book_name` → `update_book`).
 *
 * Builds the `$set` from non-null fields only, ALWAYS bumps `dateUpdated = now`
 * and ALWAYS writes `chapterCount` (legacy `BookUpdate.chapterCount` defaults to
 * 0, so `model_dump(exclude_none=True)` never drops it). Returns the updated
 * doc; a missing book / no-op update raised a 400 in the legacy route.
 */
export async function updateBook(bookId: string, update: BookUpdateInput): Promise<BookDoc> {
  await db();

  if (!isValidObjectId(bookId)) {
    throw new HttpError(400, "No changes made or book not found.");
  }

  const set: Record<string, unknown> = {
    dateUpdated: nowIso(),
    chapterCount: update.chapterCount ?? 0,
  };
  if (update.name !== null && update.name !== undefined) set.name = update.name;
  if (update.number !== null && update.number !== undefined) set.number = update.number;
  if (update.chapters !== null && update.chapters !== undefined) set.chapters = update.chapters;

  const updated = await Book.findByIdAndUpdate(bookId, { $set: set }, { new: true }).lean<BookDoc>();
  if (!updated) {
    throw new HttpError(400, "No changes made or book not found.");
  }
  return updated;
}
