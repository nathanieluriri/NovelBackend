/**
 * cache_summary projections (schema.md §4 "Embedded summary projections").
 * Mirrors legacy `core/entity_cache.py` `_build_*_summary` builders: raw field
 * passthrough (no status→accessType mapping), dates normalized to `+00:00`.
 */
import { toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, docId, numOrDefault, numOrNull, strOrNull } from "./common";
import type { ChapterAccessType } from "./chapter";

export interface BookSummaryOut {
  id: string;
  name: string | null;
  number: number | null;
  chapterCount: number;
  dateCreated: string | null;
  dateUpdated: string | null;
}

export interface ChapterSummaryOut {
  id: string;
  bookId: string | null;
  chapterLabel: string | null;
  number: number | null;
  accessType: ChapterAccessType | null;
  coverImage: string | null;
  pageCount: number;
  dateCreated: string | null;
  dateUpdated: string | null;
}

export interface PageSummaryOut {
  id: string;
  chapterId: string | null;
  status: string | null;
  number: number | null;
  textCount: number;
  dateCreated: string | null;
  dateUpdated: string | null;
}

export function toBookSummary(doc: AnyDoc): BookSummaryOut {
  return {
    id: docId(doc),
    name: strOrNull(doc.name),
    number: numOrNull(doc.number),
    chapterCount: numOrDefault(doc.chapterCount, 0),
    dateCreated: toIsoOffset(doc.dateCreated),
    dateUpdated: toIsoOffset(doc.dateUpdated),
  };
}

export function toChapterSummary(doc: AnyDoc): ChapterSummaryOut {
  return {
    id: docId(doc),
    bookId: strOrNull(doc.bookId),
    chapterLabel: strOrNull(doc.chapterLabel),
    number: numOrNull(doc.number),
    accessType: strOrNull(doc.accessType) as ChapterAccessType | null,
    coverImage: strOrNull(doc.coverImage),
    pageCount: numOrDefault(doc.pageCount, 0),
    dateCreated: toIsoOffset(doc.dateCreated),
    dateUpdated: toIsoOffset(doc.dateUpdated),
  };
}

export function toPageSummary(doc: AnyDoc): PageSummaryOut {
  return {
    id: docId(doc),
    chapterId: strOrNull(doc.chapterId),
    status: strOrNull(doc.status),
    number: numOrNull(doc.number),
    textCount: numOrDefault(doc.textCount, 0),
    dateCreated: toIsoOffset(doc.dateCreated),
    dateUpdated: toIsoOffset(doc.dateUpdated),
  };
}
