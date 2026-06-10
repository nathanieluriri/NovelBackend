/**
 * Entity-summary cache (Redis / Upstash) — port of legacy
 * `core/entity_cache.py` + `core/cache_invalidation.py`.
 *
 * Lazy (cache-aside) summary cache for exactly three entities:
 * book | chapter | page. Key scheme `summary:{type}:{id}:v1`, TTL 900s,
 * value = compact JSON of the summary with null/undefined keys removed
 * (legacy pydantic `model_dump(exclude_none=True)`).
 *
 * Every Redis op is BEST-EFFORT (rGet/rSetEx/rDel already swallow errors) —
 * Redis failures degrade to the DB and never break a request.
 *
 * See ../nextjs-migration/caching.md.
 */
import { db } from "@/lib/db";
import { rGet, rSetEx, rDel } from "@/lib/redis";
import { Book, Chapter, Page } from "@/lib/models";
import { toBookSummary, toChapterSummary, toPageSummary } from "@/lib/serializers";

export type BookSummary = ReturnType<typeof toBookSummary>;
export type ChapterSummary = ReturnType<typeof toChapterSummary>;
export type PageSummary = ReturnType<typeof toPageSummary>;

const CACHE_TTL_SECONDS = 900;
const SUMMARY_CACHE_VERSION = "v1";

type EntityType = "book" | "chapter" | "page";
type Loose = Record<string, unknown>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyDoc = Record<string, any>; // loose doc type at the serializer seam

function buildKey(entityType: EntityType, entityId: string): string {
  return `summary:${entityType}:${entityId}:${SUMMARY_CACHE_VERSION}`;
}

/** Compact JSON (no spaces), null/undefined keys removed — legacy `exclude_none`. */
function compactJson(payload: Loose): string {
  const out: Loose = {};
  for (const [k, v] of Object.entries(payload)) {
    if (v !== null && v !== undefined) out[k] = v;
  }
  return JSON.stringify(out);
}

/** Safe parse of a cached value; null on anything that is not a plain object with an id. */
function safeJsonLoads(raw: string): Loose | null {
  let loaded: unknown;
  try {
    loaded = JSON.parse(raw);
  } catch {
    return null;
  }
  if (loaded === null || typeof loaded !== "object" || Array.isArray(loaded)) return null;
  const obj = loaded as Loose;
  if (typeof obj.id !== "string" || obj.id.length === 0) return null;
  return obj;
}

// ---------------------------------------------------------------------------
// Cache-hit re-hydration. The cached payload excludes null keys, so we restore
// pydantic defaults exactly as legacy `*SummaryOut.model_validate(cached)` did
// (missing optionals -> null, missing counts -> 0). Field order mirrors the
// legacy schemas (schema.md §4 "Embedded summary projections").
// ---------------------------------------------------------------------------

function hydrateBook(raw: Loose): BookSummary {
  return {
    id: String(raw.id),
    name: raw.name ?? null,
    number: raw.number ?? null,
    chapterCount: raw.chapterCount ?? 0,
    dateCreated: raw.dateCreated ?? null,
    dateUpdated: raw.dateUpdated ?? null,
  } as unknown as BookSummary;
}

function hydrateChapter(raw: Loose): ChapterSummary {
  return {
    id: String(raw.id),
    bookId: raw.bookId ?? null,
    chapterLabel: raw.chapterLabel ?? null,
    number: raw.number ?? null,
    accessType: raw.accessType ?? null,
    coverImage: raw.coverImage ?? null,
    pageCount: raw.pageCount ?? 0,
    dateCreated: raw.dateCreated ?? null,
    dateUpdated: raw.dateUpdated ?? null,
  } as unknown as ChapterSummary;
}

function hydratePage(raw: Loose): PageSummary {
  return {
    id: String(raw.id),
    chapterId: raw.chapterId ?? null,
    status: raw.status ?? null,
    number: raw.number ?? null,
    textCount: raw.textCount ?? 0,
    dateCreated: raw.dateCreated ?? null,
    dateUpdated: raw.dateUpdated ?? null,
  } as unknown as PageSummary;
}

// ---------------------------------------------------------------------------
// DB loaders. Legacy repos resolve via `maybe_id` — an id that is not a valid
// ObjectId behaves like "not found" (returns null, never throws).
// ---------------------------------------------------------------------------

const OBJECT_ID_RE = /^[a-fA-F0-9]{24}$/;

type FindableModel = { findById(id: string): { lean(): PromiseLike<unknown> } };

async function findDoc(model: FindableModel, id: string): Promise<Loose | null> {
  if (!id || !OBJECT_ID_RE.test(id)) return null;
  await db();
  try {
    const doc = await model.findById(id).lean();
    return (doc as Loose | null) ?? null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Public API (cache-aside)
// ---------------------------------------------------------------------------

export async function getBookSummary(id: string): Promise<BookSummary | null> {
  const key = buildKey("book", id);
  const raw = await rGet(key);
  if (raw) {
    const cached = safeJsonLoads(raw);
    if (cached) return hydrateBook(cached);
  }
  const doc = await findDoc(Book as unknown as FindableModel, id);
  if (!doc) return null;
  const summary = toBookSummary(doc as AnyDoc);
  await rSetEx(key, CACHE_TTL_SECONDS, compactJson(summary as unknown as Loose));
  return summary;
}

export async function getChapterSummary(id: string): Promise<ChapterSummary | null> {
  const key = buildKey("chapter", id);
  const raw = await rGet(key);
  if (raw) {
    const cached = safeJsonLoads(raw);
    if (cached) return hydrateChapter(cached);
  }
  const doc = await findDoc(Chapter as unknown as FindableModel, id);
  if (!doc) return null;
  const summary = toChapterSummary(doc as AnyDoc);
  await rSetEx(key, CACHE_TTL_SECONDS, compactJson(summary as unknown as Loose));
  return summary;
}

export async function getPageSummary(id: string): Promise<PageSummary | null> {
  const key = buildKey("page", id);
  const raw = await rGet(key);
  if (raw) {
    const cached = safeJsonLoads(raw);
    if (cached) return hydratePage(cached);
  }
  const doc = await findDoc(Page as unknown as FindableModel, id);
  if (!doc) return null;
  const summary = toPageSummary(doc as AnyDoc);
  await rSetEx(key, CACHE_TTL_SECONDS, compactJson(summary as unknown as Loose));
  return summary;
}

/**
 * Delete-on-write invalidation (legacy `@invalidate_entity_cache`).
 * Call after every mutating book/chapter/page route — pass every id you can
 * collect from path params AND the response (`id`, `bookId`, `chapterId`);
 * parents must be busted too (counts live on the parent). Falsy ids are
 * skipped, duplicates deduped. Best-effort: never throws.
 */
export async function invalidateSummaries(ids: {
  books?: string[];
  chapters?: string[];
  pages?: string[];
}): Promise<void> {
  const keys = new Set<string>();
  for (const id of ids.books ?? []) {
    if (id) keys.add(buildKey("book", String(id)));
  }
  for (const id of ids.chapters ?? []) {
    if (id) keys.add(buildKey("chapter", String(id)));
  }
  for (const id of ids.pages ?? []) {
    if (id) keys.add(buildKey("page", String(id)));
  }
  if (keys.size) await rDel(...keys);
}
