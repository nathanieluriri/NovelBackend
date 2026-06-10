/**
 * ChapterOut / ChapterOutSyncVersion — schema.md §4.
 * pageCount/pages/commentsCount/likesCount are recomputed by the caller (DB
 * aggregation) and passed via `extras`; doc values are only fallbacks.
 * Legacy `status` → `accessType` mapping mirrors LEGACY_STATUS_TO_ACCESS in
 * `schemas/chapter_schema.py` (premium/locked → paid; unknown/missing → free).
 */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, docId, numOrDefault, strArrOrNull, strOrNull } from "./common";

export type ChapterAccessType = "free" | "subscription" | "paid";

const LEGACY_STATUS_TO_ACCESS: Record<string, ChapterAccessType> = {
  free: "free",
  subscription: "subscription",
  paid: "paid",
  premium: "paid",
  locked: "paid",
};

function resolveAccessType(doc: AnyDoc): ChapterAccessType {
  const access = doc.accessType;
  if (access === "free" || access === "subscription" || access === "paid") return access;
  const status = doc.status;
  if (status !== null && status !== undefined) {
    const mapped = LEGACY_STATUS_TO_ACCESS[String(status).trim().toLowerCase()];
    if (mapped) return mapped;
  }
  return "free";
}

export interface ChapterOut {
  bookId: string;
  chapterLabel: string | null;
  status: string | null;
  accessType: ChapterAccessType;
  unlockBundleId: string | null;
  number: number;
  id: string;
  coverImage: string | null;
  lastAccessed: string;
  dateCreated: string | null;
  dateUpdated: string | null;
  pageCount: number;
  pages: string[] | null;
  commentsCount: number;
  likesCount: number;
}

/** RecentChapterOut = ChapterOut + wordCount (admin dashboard). */
export interface RecentChapterOut extends ChapterOut {
  wordCount: number;
}

/** ChapterBase fields + id + hasRead (UserOutChapterDetails.chapterDetails). */
export interface ChapterOutSyncVersion {
  bookId: string;
  chapterLabel: string | null;
  status: string | null;
  accessType: ChapterAccessType;
  unlockBundleId: string | null;
  coverImage: string | null;
  number: number;
  id: string;
  hasRead: boolean;
}

export interface ChapterOutExtras {
  pageCount?: number;
  pages?: string[] | null;
  commentsCount?: number;
  likesCount?: number;
}

export function toChapterOut(doc: AnyDoc, extras?: ChapterOutExtras): ChapterOut {
  return {
    bookId: String(doc.bookId ?? ""),
    chapterLabel: strOrNull(doc.chapterLabel),
    status: strOrNull(doc.status),
    accessType: resolveAccessType(doc),
    unlockBundleId: strOrNull(doc.unlockBundleId),
    number: numOrDefault(doc.number, 0),
    id: docId(doc),
    coverImage: strOrNull(doc.coverImage),
    lastAccessed: nowIso(),
    dateCreated: toIsoOffset(doc.dateCreated),
    dateUpdated: toIsoOffset(doc.dateUpdated),
    pageCount: extras?.pageCount ?? numOrDefault(doc.pageCount, 0),
    pages: extras?.pages !== undefined ? extras.pages : strArrOrNull(doc.pages),
    commentsCount: extras?.commentsCount ?? numOrDefault(doc.commentsCount, 0),
    likesCount: extras?.likesCount ?? numOrDefault(doc.likesCount, 0),
  };
}

export function toChapterSyncVersion(doc: AnyDoc, hasRead: boolean): ChapterOutSyncVersion {
  return {
    bookId: String(doc.bookId ?? ""),
    chapterLabel: strOrNull(doc.chapterLabel),
    status: strOrNull(doc.status),
    accessType: resolveAccessType(doc),
    unlockBundleId: strOrNull(doc.unlockBundleId),
    coverImage: strOrNull(doc.coverImage),
    number: numOrDefault(doc.number, 0),
    id: docId(doc),
    hasRead,
  };
}
