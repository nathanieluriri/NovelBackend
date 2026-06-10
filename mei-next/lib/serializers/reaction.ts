/**
 * ReactionOut — schema.md §4. ⚠ aliased: internal `date_created`/`last_updated`
 * (stored as epoch seconds) go on the wire as `dateCreated`/`lastUpdated` ISO
 * `+00:00` strings (schema.md §0.4).
 */
import { toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, idOrNull } from "./common";

export interface ReactionOut {
  reaction: string;
  authorRoomId: string;
  id: string | null;
  dateCreated: string | null;
  lastUpdated: string | null;
}

export function toReactionOut(doc: AnyDoc): ReactionOut {
  return {
    reaction: String(doc.reaction ?? ""),
    authorRoomId: String(doc.authorRoomId ?? ""),
    id: idOrNull(doc),
    dateCreated: toIsoOffset(doc.date_created ?? doc.dateCreated),
    lastUpdated: toIsoOffset(doc.last_updated ?? doc.lastUpdated),
  };
}
