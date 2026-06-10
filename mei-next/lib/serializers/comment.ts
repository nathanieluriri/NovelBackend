/**
 * CommentOut — schema.md §4. User fields (firstName/lastName/avatar/email) are
 * hydrated by the caller and passed as the optional `user` argument.
 * Legacy chapter-only docs (no targetType, has chapterId) are normalized to
 * targetType="chapter", targetId=chapterId — mirrors `schemas/comments_schema.py`.
 */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, docId, strOrNull } from "./common";

export type InteractionTargetType = "book" | "chapter" | "page";

export type CommentType =
  | "reply_target"
  | "Reply To Chapter"
  | "Reply To Comment"
  | "Reply To Reply";

const COMMENT_TYPES: readonly string[] = [
  "reply_target",
  "Reply To Chapter",
  "Reply To Comment",
  "Reply To Reply",
];

export interface CommentOut {
  id: string;
  userId: string;
  role: string;
  text: string;
  targetType: InteractionTargetType;
  targetId: string;
  parentCommentId: string | null;
  commentType: CommentType;
  dateCreated: string;
  firstName: string | null;
  lastName: string | null;
  avatar: string | null;
  email: string | null;
}

export interface CommentUserDetails {
  firstName?: string | null;
  lastName?: string | null;
  avatar?: string | null;
  email?: string | null;
}

export function toCommentOut(doc: AnyDoc, user?: CommentUserDetails | null): CommentOut {
  let targetType = strOrNull(doc.targetType);
  let targetId = strOrNull(doc.targetId);
  // Compatibility with old chapter-only comments.
  if (targetType === null && doc.chapterId !== null && doc.chapterId !== undefined) {
    targetType = "chapter";
    targetId = String(doc.chapterId);
  }
  const rawType = strOrNull(doc.commentType);
  return {
    id: docId(doc),
    userId: String(doc.userId ?? ""),
    role: String(doc.role ?? ""),
    text: String(doc.text ?? ""),
    targetType: (targetType ?? "chapter") as InteractionTargetType,
    targetId: targetId ?? "",
    parentCommentId: strOrNull(doc.parentCommentId),
    commentType: (rawType !== null && COMMENT_TYPES.includes(rawType) ? rawType : "reply_target") as CommentType,
    dateCreated: toIsoOffset(doc.dateCreated) ?? nowIso(),
    firstName: strOrNull(user?.firstName),
    lastName: strOrNull(user?.lastName),
    avatar: strOrNull(user?.avatar),
    email: strOrNull(user?.email),
  };
}
