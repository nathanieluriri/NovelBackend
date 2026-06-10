/** PageOut — schema.md §4. `lastAccessed` is computed at serialize time (= now). */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, docId, numOrDefault } from "./common";

export interface PageOut {
  chapterId: string;
  textContent: string;
  status: string;
  dateCreated: string | null;
  dateUpdated: string | null;
  textCount: number;
  id: string;
  lastAccessed: string;
}

export function toPageOut(doc: AnyDoc): PageOut {
  return {
    // Some very old docs store snake_case `chapter_id`.
    chapterId: String(doc.chapterId ?? doc.chapter_id ?? ""),
    textContent: String(doc.textContent ?? ""),
    status: String(doc.status ?? ""),
    dateCreated: toIsoOffset(doc.dateCreated),
    dateUpdated: toIsoOffset(doc.dateUpdated),
    textCount: numOrDefault(doc.textCount, 0),
    id: docId(doc),
    lastAccessed: nowIso(),
  };
}
