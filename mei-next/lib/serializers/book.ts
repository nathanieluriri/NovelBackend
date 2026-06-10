/** BookOut — schema.md §4. `lastAccessed` is computed at serialize time (= now). */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, docId, numOrDefault, strArrOrNull } from "./common";

export interface BookOut {
  name: string;
  number: number;
  dateCreated: string | null;
  dateUpdated: string | null;
  chapterCount: number;
  chapters: string[] | null;
  id: string;
  lastAccessed: string;
}

export function toBookOut(doc: AnyDoc): BookOut {
  return {
    name: String(doc.name ?? ""),
    number: numOrDefault(doc.number, 0),
    dateCreated: toIsoOffset(doc.dateCreated),
    dateUpdated: toIsoOffset(doc.dateUpdated),
    chapterCount: numOrDefault(doc.chapterCount, 0),
    chapters: strArrOrNull(doc.chapters),
    id: docId(doc),
    lastAccessed: nowIso(),
  };
}
