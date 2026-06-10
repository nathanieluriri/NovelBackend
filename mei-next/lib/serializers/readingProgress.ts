/** ReadingProgressOut — schema.md §4. Summaries are caller-provided enrichment. */
import { toIsoOffset } from "@/lib/util/dates";
import type { AnyDoc } from "./common";
import type { ChapterSummaryOut, PageSummaryOut } from "./summaries";

export interface ReadingProgressOut {
  userId: string;
  chapterId: string;
  pageId: string;
  dateUpdated: string | null;
  chapterSummary: ChapterSummaryOut | null;
  pageSummary: PageSummaryOut | null;
}

export interface ReadingProgressOutExtras {
  chapterSummary?: ChapterSummaryOut | null;
  pageSummary?: PageSummaryOut | null;
}

export function toReadingProgressOut(doc: AnyDoc, extras?: ReadingProgressOutExtras): ReadingProgressOut {
  return {
    userId: String(doc.userId ?? ""),
    chapterId: String(doc.chapterId ?? ""),
    pageId: String(doc.pageId ?? ""),
    dateUpdated: toIsoOffset(doc.dateUpdated),
    chapterSummary: extras?.chapterSummary ?? null,
    pageSummary: extras?.pageSummary ?? null,
  };
}
