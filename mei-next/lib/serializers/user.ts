/**
 * UserOut / NewUserOut / OldUserOut — schema.md §4.
 * - UserOut has `status`; NewUserOut omits it; OldUserOut requires non-null
 *   accessToken/refreshToken (same key set/order as NewUserOut).
 * - ⚠ `stopped_reading` is the one snake_case key (schema.md §0.2).
 * - `authProviders` lowercased + deduped, with the legacy `provider` appended
 *   (mirrors `_normalize_auth_providers` in `schemas/user_schema.py`).
 * - Defaults: balance 0, stage {currentStage:1, currentExperience:0},
 *   subscription {active:false, expiresAt:null}.
 */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, numOrDefault, numOrNull, strArrOrNull, strOrNull } from "./common";
import type { BookMarkOut } from "./bookmark";
import type { ChapterOutSyncVersion } from "./chapter";
import type { LikeOut } from "./like";

export type UserStatus = "Active" | "Inactive" | "Suspended";

export interface Stage {
  currentStage: number;
  currentExperience: number;
}

export interface ReadingHistory {
  chapterId: string | null;
  chapterNumber: number | null;
  chapterSnippet: string | null;
}

export interface SubscriptionInfo {
  active: boolean;
  expiresAt: string | null;
}

export interface UserOut {
  userId: string;
  status: UserStatus | null;
  email: string;
  firstName: string | null;
  lastName: string | null;
  avatar: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  balance: number;
  unlockedChapters: string[] | null;
  dateCreated: string;
  stage: Stage;
  bookmarks: BookMarkOut[];
  likes: LikeOut[];
  stopped_reading: ReadingHistory | null;
  authProviders: string[];
  subscription: SubscriptionInfo;
}

/** UserOut + chapterDetails (admin user detail view). */
export interface UserOutChapterDetails extends UserOut {
  chapterDetails: ChapterOutSyncVersion[];
}

/** Signup response — same keys as UserOut minus `status`, in legacy key order. */
export interface NewUserOut {
  userId: string;
  email: string;
  balance: number;
  accessToken: string | null;
  refreshToken: string | null;
  unlockedChapters: string[];
  firstName: string | null;
  lastName: string | null;
  avatar: string | null;
  dateCreated: string;
  stage: Stage;
  bookmarks: BookMarkOut[];
  likes: LikeOut[];
  stopped_reading: ReadingHistory | null;
  authProviders: string[];
  subscription: SubscriptionInfo;
}

/** Signin response — NewUserOut with required (non-null) tokens. */
export interface OldUserOut extends NewUserOut {
  accessToken: string;
  refreshToken: string;
}

export interface UserExtras {
  accessToken?: string | null;
  refreshToken?: string | null;
  bookmarks?: BookMarkOut[];
  likes?: LikeOut[];
  stopped_reading?: ReadingHistory | null;
  chapterDetails?: ChapterOutSyncVersion[];
}

export interface OldUserExtras extends UserExtras {
  accessToken: string;
  refreshToken: string;
}

function normalizeAuthProviders(doc: AnyDoc): string[] {
  const out: string[] = [];
  const push = (v: unknown) => {
    if (typeof v !== "string") return;
    const candidate = v.trim().toLowerCase();
    if (candidate && !out.includes(candidate)) out.push(candidate);
  };
  if (Array.isArray(doc?.authProviders)) for (const item of doc.authProviders) push(item);
  push(doc?.provider);
  return out;
}

function buildStage(doc: AnyDoc): Stage {
  const raw = doc?.stage;
  if (raw && typeof raw === "object") {
    return {
      currentStage: numOrDefault((raw as AnyDoc).currentStage, 1),
      currentExperience: numOrDefault((raw as AnyDoc).currentExperience, 0),
    };
  }
  return { currentStage: 1, currentExperience: 0 };
}

function buildSubscription(doc: AnyDoc): SubscriptionInfo {
  const raw = doc?.subscription;
  return {
    active: Boolean((raw as AnyDoc | null | undefined)?.active ?? false),
    expiresAt: strOrNull((raw as AnyDoc | null | undefined)?.expiresAt),
  };
}

function buildStoppedReading(value: unknown): ReadingHistory | null {
  if (!value || typeof value !== "object") return null;
  const v = value as AnyDoc;
  return {
    chapterId: strOrNull(v.chapterId),
    chapterNumber: numOrNull(v.chapterNumber),
    chapterSnippet: strOrNull(v.chapterSnippet),
  };
}

function resolveStoppedReading(doc: AnyDoc, extras?: UserExtras): ReadingHistory | null {
  if (extras && "stopped_reading" in extras) return buildStoppedReading(extras.stopped_reading);
  return buildStoppedReading(doc.stopped_reading);
}

/** Legacy UserOut: `_id` wins over a pre-set `userId` key. */
function resolveUserId(doc: AnyDoc): string {
  if (doc._id !== null && doc._id !== undefined) return String(doc._id);
  return String(doc.userId ?? doc.id ?? "");
}

export function toUserOut(
  doc: AnyDoc,
  extras: UserExtras & { chapterDetails: ChapterOutSyncVersion[] },
): UserOutChapterDetails;
export function toUserOut(doc: AnyDoc, extras?: UserExtras): UserOut;
export function toUserOut(doc: AnyDoc, extras?: UserExtras): UserOut {
  const out: UserOut = {
    userId: resolveUserId(doc),
    status: strOrNull(doc.status) as UserStatus | null,
    email: String(doc.email ?? ""),
    firstName: strOrNull(doc.firstName),
    lastName: strOrNull(doc.lastName),
    avatar: strOrNull(doc.avatar),
    accessToken: strOrNull(extras?.accessToken ?? doc.accessToken),
    refreshToken: strOrNull(extras?.refreshToken ?? doc.refreshToken),
    balance: numOrDefault(doc.balance, 0),
    unlockedChapters: strArrOrNull(doc.unlockedChapters),
    dateCreated: toIsoOffset(doc.dateCreated) ?? nowIso(),
    stage: buildStage(doc),
    bookmarks: extras?.bookmarks ?? [],
    likes: extras?.likes ?? [],
    stopped_reading: resolveStoppedReading(doc, extras),
    authProviders: normalizeAuthProviders(doc),
    subscription: buildSubscription(doc),
  };
  const chapterDetails = extras?.chapterDetails;
  if (chapterDetails !== undefined) {
    (out as UserOutChapterDetails).chapterDetails = chapterDetails;
  }
  return out;
}

export function toNewUserOut(doc: AnyDoc, extras?: UserExtras): NewUserOut {
  return {
    userId: resolveUserId(doc),
    email: String(doc.email ?? ""),
    balance: numOrDefault(doc.balance, 0),
    accessToken: strOrNull(extras?.accessToken ?? doc.accessToken),
    refreshToken: strOrNull(extras?.refreshToken ?? doc.refreshToken),
    unlockedChapters: strArrOrNull(doc.unlockedChapters) ?? [],
    firstName: strOrNull(doc.firstName),
    lastName: strOrNull(doc.lastName),
    avatar: strOrNull(doc.avatar),
    dateCreated: toIsoOffset(doc.dateCreated) ?? nowIso(),
    stage: buildStage(doc),
    bookmarks: extras?.bookmarks ?? [],
    likes: extras?.likes ?? [],
    stopped_reading: resolveStoppedReading(doc, extras),
    authProviders: normalizeAuthProviders(doc),
    subscription: buildSubscription(doc),
  };
}

export function toOldUserOut(doc: AnyDoc, extras: OldUserExtras): OldUserOut {
  return {
    ...toNewUserOut(doc, extras),
    accessToken: String(extras.accessToken),
    refreshToken: String(extras.refreshToken),
  };
}
