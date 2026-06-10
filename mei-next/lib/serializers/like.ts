/**
 * LikeOut / LikeWithUserOut — schema.md §4.
 * ⚠ `chapaterLabel` is DELIBERATELY misspelled on the wire — required field.
 */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, idOrNull, strOrNull } from "./common";
import type { ChapterSummaryOut } from "./summaries";

export type LikeType =
  | "Liked Chapter"
  | "Liked Comment"
  | "Liked Comment Reply"
  | "Liked Reply To Reply";

const LIKE_TYPES: readonly string[] = [
  "Liked Chapter",
  "Liked Comment",
  "Liked Comment Reply",
  "Liked Reply To Reply",
];

export interface LikeOut {
  chapterId: string;
  userId: string;
  role: string;
  likeType: LikeType;
  /** ⚠ misspelled on purpose — keep the typo (schema.md §0.1). */
  chapaterLabel: string;
  dateCreated: string;
  id: string | null;
  chapterSummary: ChapterSummaryOut | null;
}

export interface LikeUserDetailsOut {
  firstName: string | null;
  lastName: string | null;
  avatar: string | null;
  email: string | null;
}

export interface LikeWithUserOut extends LikeOut {
  user: LikeUserDetailsOut | null;
}

export function toLikeOut(doc: AnyDoc, chapterSummary?: ChapterSummaryOut | null): LikeOut {
  const rawType = strOrNull(doc.likeType);
  return {
    chapterId: String(doc.chapterId ?? ""),
    userId: String(doc.userId ?? ""),
    role: String(doc.role ?? ""),
    likeType: (rawType !== null && LIKE_TYPES.includes(rawType) ? rawType : "Liked Chapter") as LikeType,
    chapaterLabel: String(doc.chapaterLabel ?? ""),
    dateCreated: toIsoOffset(doc.dateCreated) ?? nowIso(),
    id: idOrNull(doc),
    chapterSummary: chapterSummary ?? null,
  };
}

export function toLikeWithUserOut(
  doc: AnyDoc,
  user: AnyDoc | null | undefined,
  chapterSummary?: ChapterSummaryOut | null,
): LikeWithUserOut {
  return {
    ...toLikeOut(doc, chapterSummary),
    user: user
      ? {
          firstName: strOrNull(user.firstName),
          lastName: strOrNull(user.lastName),
          avatar: strOrNull(user.avatar),
          email: strOrNull(user.email),
        }
      : null,
  };
}
