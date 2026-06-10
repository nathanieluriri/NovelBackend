/** EntitlementOut — schema.md §4. grantType defaults to "chapter_unlock". */
import { toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, idOrNull, strOrNull } from "./common";

export type EntitlementGrantType = "chapter_unlock";

export interface EntitlementOut {
  userId: string;
  chapterId: string;
  grantType: EntitlementGrantType;
  source: string | null;
  txRef: string | null;
  id: string | null;
  createdAt: string | null;
}

export function toEntitlementOut(doc: AnyDoc): EntitlementOut {
  return {
    userId: String(doc.userId ?? ""),
    chapterId: String(doc.chapterId ?? ""),
    grantType: (strOrNull(doc.grantType) ?? "chapter_unlock") as EntitlementGrantType,
    source: strOrNull(doc.source),
    txRef: strOrNull(doc.txRef),
    id: idOrNull(doc),
    createdAt: toIsoOffset(doc.createdAt),
  };
}
