/**
 * AuthorRoomOut — schema.md §4. ⚠ aliased: internal `date_created`/`last_updated`
 * (epoch seconds) → wire `dateCreated`/`lastUpdated` ISO `+00:00` strings.
 * chapterSummary/reactionSummary/userReaction are enrichment data passed by the
 * caller; `reactionSummary` defaults to an empty object.
 */
import { toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, idOrNull } from "./common";
import type { ChapterSummaryOut } from "./summaries";

export interface AuthorRoomOut {
  text: string;
  chapterId: string;
  id: string | null;
  dateCreated: string | null;
  lastUpdated: string | null;
  chapterSummary: ChapterSummaryOut | null;
  reactionSummary: Record<string, number>;
  userReaction: string | null;
}

export interface AuthorRoomOutExtras {
  chapterSummary?: ChapterSummaryOut | null;
  reactionSummary?: Record<string, number> | null;
  userReaction?: string | null;
}

export function toAuthorRoomOut(doc: AnyDoc, extras?: AuthorRoomOutExtras): AuthorRoomOut {
  return {
    text: String(doc.text ?? ""),
    chapterId: String(doc.chapterId ?? ""),
    id: idOrNull(doc),
    dateCreated: toIsoOffset(doc.date_created ?? doc.dateCreated),
    lastUpdated: toIsoOffset(doc.last_updated ?? doc.lastUpdated),
    chapterSummary: extras?.chapterSummary ?? null,
    reactionSummary: extras?.reactionSummary ?? {},
    userReaction: extras?.userReaction ?? null,
  };
}
