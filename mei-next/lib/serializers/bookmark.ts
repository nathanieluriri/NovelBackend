/**
 * BookMarkOut (Sync/Async identical) — schema.md §4.
 * Legacy page-only docs (no targetType, has pageId) normalize to
 * targetType="page", targetId=pageId — mirrors `schemas/bookmark_schema.py`.
 * `pageNumber` and `chapterSummary` are computed by the caller (extras).
 */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, idOrNull, numOrNull, strOrNull } from "./common";
import type { InteractionTargetType } from "./comment";
import type { ChapterSummaryOut } from "./summaries";

export interface BookMarkOut {
  userId: string;
  targetType: InteractionTargetType;
  targetId: string;
  chapterLabel: string | null;
  chapterId: string | null;
  pageId: string | null;
  dateCreated: string;
  id: string | null;
  pageNumber: number | null;
  chapterSummary: ChapterSummaryOut | null;
}

/** Sync/Async variants are wire-identical in the legacy app. */
export type BookMarkOutSync = BookMarkOut;
export type BookMarkOutAsync = BookMarkOut;

export interface BookmarkOutExtras {
  pageNumber?: number | null;
  chapterSummary?: ChapterSummaryOut | null;
}

export function toBookmarkOut(doc: AnyDoc, extras?: BookmarkOutExtras): BookMarkOut {
  let targetType = strOrNull(doc.targetType);
  let targetId = strOrNull(doc.targetId);
  // Compatibility with legacy page-only bookmark docs.
  if (targetType === null && doc.pageId !== null && doc.pageId !== undefined) {
    targetType = "page";
    targetId = String(doc.pageId);
  }
  return {
    userId: String(doc.userId ?? ""),
    targetType: (targetType ?? "page") as InteractionTargetType,
    targetId: targetId ?? "",
    chapterLabel: strOrNull(doc.chapterLabel),
    chapterId: strOrNull(doc.chapterId),
    pageId: strOrNull(doc.pageId),
    dateCreated: toIsoOffset(doc.dateCreated) ?? nowIso(),
    id: idOrNull(doc),
    pageNumber: extras?.pageNumber !== undefined ? extras.pageNumber : numOrNull(doc.pageNumber),
    chapterSummary: extras?.chapterSummary ?? null,
  };
}
