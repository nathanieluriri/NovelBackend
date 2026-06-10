/**
 * Page service — port of `services/page_services.py` (+ `repositories/page_repo.py`).
 * Business logic for the `/api/v2/page/*` surface (see ../nextjs-migration/endpoints.md).
 *
 * Behavioural parity notes (reproduced EXACTLY — do not "fix"):
 *  - `textCount` = word count of HTML-stripped `textContent` (legacy `clean_html`
 *    via BeautifulSoup `get_text(separator=" ", strip=True)`, then `len(split())`).
 *  - On CREATE, the parent chapter's `pageCount`/`pages` are recomputed from the
 *    page set *before* the new page is inserted — i.e. the new page is NOT counted
 *    until the next chapter-touching write. This is a legacy quirk; keep it.
 *  - On UPDATE/DELETE, the chapter is recomputed from the *current* page set.
 *  - User read paths load the chapter and gate via hasChapterAccess (403).
 */
import { Types } from "mongoose";
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { nowIso } from "@/lib/util/dates";
import { Page, Chapter, type PageDoc, type ChapterDoc, type UserDoc } from "@/lib/models";
import { hasChapterAccess } from "@/lib/services/access";
import { toPageOut, type PageOut } from "@/lib/serializers";

type LeanPage = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// ---------------------------------------------------------------------------
// HTML stripping / word count (port of `schemas/utils.py::clean_html`)
// ---------------------------------------------------------------------------

/**
 * Strip HTML to plain text the way legacy `clean_html` did:
 *  - remove <script>/<style> elements (incl. their contents),
 *  - replace remaining tags with a separator space (BeautifulSoup `get_text(sep=" ")`),
 *  - collapse whitespace and trim (BeautifulSoup `strip=True`).
 */
export function cleanHtml(html: string): string {
  const withoutScriptStyle = String(html ?? "").replace(
    /<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,
    " ",
  );
  const withoutTags = withoutScriptStyle.replace(/<[^>]*>/g, " ");
  return withoutTags.replace(/\s+/g, " ").trim();
}

/** Word count of cleaned HTML — `len(clean_html(text).split())`. */
export function textCountOf(html: string): number {
  const cleaned = cleanHtml(html);
  if (!cleaned) return 0;
  return cleaned.split(/\s+/).filter(Boolean).length;
}

// ---------------------------------------------------------------------------
// Chapter recompute helper (legacy `update_chapter(pageCount, pages)`)
// ---------------------------------------------------------------------------

/**
 * Recompute a chapter's `pageCount`/`pages` from a list of page docs. Mirrors
 * the legacy `update_chapter(ChapterUpdate(pageCount, pages))` which also bumps
 * `dateUpdated` (the schema's before-validator sets it on every write).
 */
async function syncChapterPages(chapterId: string, pages: LeanPage[]): Promise<void> {
  if (!Types.ObjectId.isValid(chapterId)) return;
  const pageIds = pages.map((p) => String(p._id));
  await Chapter.updateOne(
    { _id: chapterId },
    { $set: { pageCount: pages.length, pages: pageIds, dateUpdated: nowIso() } },
  );
}

async function getAllPages(chapterId: string): Promise<LeanPage[]> {
  return Page.find({ chapterId }).lean<LeanPage[]>();
}

// ---------------------------------------------------------------------------
// List / single fetch — admin vs user
// ---------------------------------------------------------------------------

/** Admin list: pages by chapter, paginated. */
export async function fetchPages(
  chapterId: string,
  skip = 0,
  limit?: number,
): Promise<PageOut[]> {
  await db();
  let q = Page.find({ chapterId }).skip(skip);
  if (limit !== undefined && limit !== null) q = q.limit(limit);
  const pages = await q.lean<LeanPage[]>();
  return pages.map((p) => toPageOut(p));
}

/** User list: load chapter, gate access (403), then the same list. */
export async function fetchPagesForUser(
  chapterId: string,
  user: UserDoc,
  skip = 0,
  limit?: number,
): Promise<PageOut[]> {
  await db();
  const chapter = await Chapter.findById(chapterId).lean<ChapterDoc>();
  if (!chapter) throw new HttpError(404, "Chapter not found");

  const canAccess = await hasChapterAccess(user, chapter);
  if (!canAccess) throw new HttpError(403, "You do not have access to this chapter");

  return fetchPages(chapterId, skip, limit);
}

/** Admin single page by id. Legacy returns PageOut even when the doc is null. */
export async function fetchSinglePageByPageId(pageId: string): Promise<PageOut> {
  await db();
  const page = await Page.findById(pageId).lean<LeanPage>();
  return toPageOut(page ?? {});
}

/**
 * User single page by id: 404 if missing, load chapter (404 if missing), gate
 * access (403), then return the page. Returns the raw lean doc alongside the
 * wire shape so the route can read `chapterId` for the reading-progress upsert.
 */
export async function fetchSinglePageByPageIdForUser(
  pageId: string,
  user: UserDoc,
): Promise<{ pageOut: PageOut; chapterId: string }> {
  await db();
  const page = await Page.findById(pageId).lean<LeanPage>();
  if (!page) throw new HttpError(404, "Page not found");

  const chapterId = String(page.chapterId ?? "");
  const chapter = await Chapter.findById(chapterId).lean<ChapterDoc>();
  if (!chapter) throw new HttpError(404, "Chapter not found");

  const canAccess = await hasChapterAccess(user, chapter);
  if (!canAccess) throw new HttpError(403, "You do not have access to this chapter");

  return { pageOut: toPageOut(page), chapterId };
}

/** Total pages in a chapter (for pagination meta). */
export async function fetchPagesCount(chapterId: string): Promise<number> {
  await db();
  return Page.countDocuments({ chapterId });
}

// ---------------------------------------------------------------------------
// Create / update / delete
// ---------------------------------------------------------------------------

/**
 * Create a page (`textCount` from cleaned HTML; no `number` field — see below).
 * The parent chapter is then recomputed from the page set *before* this insert
 * (legacy quirk: the new page is not counted until the next chapter write).
 */
export async function addPage(args: {
  bookId: string;
  chapterId: string;
  textContent: string;
  status: string;
}): Promise<PageOut> {
  await db();
  const existing = await getAllPages(args.chapterId);
  const now = nowIso();
  // Parity: legacy `create_page` raw-inserts exactly the dumped `PageCreate`
  // dict — `{chapterId, textContent, status, dateCreated, dateUpdated, textCount}`.
  // It does NOT persist `number` (the kwarg is ignored by Pydantic). Use the raw
  // driver so the Mongoose `number` default (0) isn't applied — keeps the stored
  // doc (and its PageSummary) byte-equivalent to legacy.
  const doc: Record<string, unknown> = {
    chapterId: args.chapterId,
    textContent: args.textContent,
    status: args.status,
    dateCreated: now,
    dateUpdated: now,
    textCount: textCountOf(args.textContent),
  };
  const { insertedId } = await Page.collection.insertOne(doc);

  // Legacy `update_chapter` runs with the PRE-insert page list (count + ids).
  await syncChapterPages(args.chapterId, existing);

  return toPageOut({ ...doc, _id: insertedId } as PageDoc);
}

/**
 * Update a page's content/status. Recomputes `textCount`, bumps `dateUpdated`,
 * then recomputes the parent chapter from the current page set.
 */
export async function updatePageContent(args: {
  pageId: string;
  textContent: string;
  status?: string | null;
}): Promise<PageOut | null> {
  await db();
  const now = nowIso();
  const set: Record<string, unknown> = {
    textContent: args.textContent,
    textCount: textCountOf(args.textContent),
    dateUpdated: now,
  };
  if (args.status !== undefined && args.status !== null) set.status = args.status;

  const updated = await Page.findByIdAndUpdate(
    args.pageId,
    { $set: set },
    { new: true },
  ).lean<LeanPage>();
  if (!updated) return null;

  const chapterId = String(updated.chapterId ?? "");
  const pages = await getAllPages(chapterId);
  await syncChapterPages(chapterId, pages);

  return toPageOut(updated);
}

/**
 * Delete a page. 404 (via null return → route raises) when it does not exist.
 * Recomputes the parent chapter from the remaining page set.
 */
export async function deletePage(pageId: string): Promise<PageOut | null> {
  await db();
  const removed = await Page.findByIdAndDelete(pageId).lean<LeanPage>();
  if (!removed) return null;

  const chapterId = String(removed.chapterId ?? "");
  const pages = await getAllPages(chapterId);
  await syncChapterPages(chapterId, pages);

  return toPageOut(removed);
}
