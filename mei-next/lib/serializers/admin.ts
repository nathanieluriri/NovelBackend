/**
 * Admin / dashboard wire schemas — schema.md §4 "Admin / dashboard".
 * NewAdminOut tokens are issued by the caller and passed via extras.
 * Note `PageAnalytics.totalpages` lowercase "p" — legacy field name, keep it.
 */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, idOrNull, numOrDefault, strOrNull } from "./common";
import type { RecentChapterOut } from "./chapter";
import type { UserOut } from "./user";

export interface NewAdminOut {
  email: string;
  invitedBy: string | null;
  userId: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  firstName: string | null;
  lastName: string | null;
  avatar: string | null;
  dateCreated: string;
}

export interface NewAdminOutExtras {
  accessToken?: string | null;
  refreshToken?: string | null;
}

export function toNewAdminOut(doc: AnyDoc, extras?: NewAdminOutExtras): NewAdminOut {
  return {
    email: String(doc.email ?? ""),
    invitedBy: strOrNull(doc.invitedBy),
    userId: idOrNull(doc),
    accessToken: strOrNull(extras?.accessToken ?? doc.accessToken),
    refreshToken: strOrNull(extras?.refreshToken ?? doc.refreshToken),
    firstName: strOrNull(doc.firstName),
    lastName: strOrNull(doc.lastName),
    avatar: strOrNull(doc.avatar),
    dateCreated: toIsoOffset(doc.dateCreated) ?? nowIso(),
  };
}

export interface ChapterInteractionUserOut {
  userId: string;
  firstName: string | null;
  lastName: string | null;
  email: string | null;
  avatar: string | null;
  interactionCount: number;
  lastInteractionAt: string | null;
}

export function toChapterInteractionUserOut(
  user: AnyDoc,
  interactionCount: number,
  lastInteractionAt: string | number | Date | null | undefined,
): ChapterInteractionUserOut {
  return {
    userId: String(user.userId ?? user._id ?? ""),
    firstName: strOrNull(user.firstName),
    lastName: strOrNull(user.lastName),
    email: strOrNull(user.email),
    avatar: strOrNull(user.avatar),
    interactionCount: numOrDefault(interactionCount, 0),
    lastInteractionAt: toIsoOffset(lastInteractionAt),
  };
}

// --- Dashboard analytics shapes (assembled by the admin service) ---

export type ChangeType = "increase" | "decrease" | "no change";

export interface ChapterAnalytics {
  totalChapters: string | null;
  chapterChange: string | null;
  changeType: ChangeType | null;
}

export interface PageAnalytics {
  /** lowercase "p" — legacy field name. */
  totalpages: string | null;
  pageChange: string | null;
  changeType: ChangeType | null;
}

export interface ReaderAnalytics {
  totalReaders: string | null;
  readerChange: string | null;
  changeType: ChangeType | null;
}

export interface RevenueAnalytics {
  totalRevenue: string | null;
  revenueChange: string | null;
  changeType: ChangeType | null;
}

export interface AdminDashboardAnalytics {
  chapterAnalytics: ChapterAnalytics;
  pageAnalytics: PageAnalytics;
  readerAnalytics: ReaderAnalytics;
  revenueAnalytics: RevenueAnalytics;
  recentChapters: RecentChapterOut[];
  recentUsers: UserOut[];
}
