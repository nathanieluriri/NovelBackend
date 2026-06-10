/**
 * Payment wire schemas — schema.md §4 "Payment schemas".
 * - ⚠ TransactionOut.TransactionType is PascalCase on the wire (schema.md §0.3).
 * - bundleType "subscription" is normalized to "subscriptionCash" on read.
 * - Bundle `dateCreated` is stored as epoch seconds → ISO `+00:00`.
 */
import { nowIso, toIsoOffset } from "@/lib/util/dates";
import { type AnyDoc, docId, numOrDefault, numOrNull, strOrNull } from "./common";

export type TransactionType =
  | "cash"
  | "transferOfStarCurrencyBetweenAccounts"
  | "transferOfStarCurrencyForChapterAccess"
  | "subscriptionPurchase";

export type BundleType =
  | "cash"
  | "purchaseOfBooks"
  | "transferringStarsToOtherUsers"
  | "cashPromo"
  | "bookPromo"
  | "subscription"
  | "subscriptionCash"
  | "subscriptionStars";

export type PaymentProvider = "flutterwave" | "paystack" | "stripe";

export type PaymentStatus = "initiated" | "pending" | "verified" | "fulfilled" | "failed";

export interface CheckoutSessionOut {
  checkoutUrl: string;
  provider: PaymentProvider;
  providerReference: string;
  txRef: string;
  status: PaymentStatus;
  expiresAt: string | null;
}

export interface PaymentBundlesOut {
  id: string;
  amount: number | null;
  numberOfstars: number | null;
  bundleType: BundleType | null;
  durationDays: number | null;
  description: string;
  dateCreated: string | null;
}

export interface PricingBundleOut {
  id: string;
  bundleType: BundleType;
  description: string;
  durationDays: number | null;
  cashAmount: number | null;
  starAmount: number | null;
  dateCreated: string | null;
}

export interface PricingCatalogOut {
  subscriptionPlans: PricingBundleOut[];
  starBundles: PricingBundleOut[];
  chapterUnlockBundles: PricingBundleOut[];
}

export interface TransactionOut {
  id: string;
  userId: string;
  paymentId: string;
  numberOfStars: number;
  /** ⚠ PascalCase wire field — keep as-is. */
  TransactionType: TransactionType;
  amount: number;
  dateCreated: string;
}

/** Legacy quirk: "subscription" bundles are read back as "subscriptionCash". */
function normalizeBundleType(raw: unknown): BundleType | null {
  const value = strOrNull(raw);
  if (value === null) return null;
  if (value === "subscription") return "subscriptionCash";
  return value as BundleType;
}

export function toPaymentBundlesOut(doc: AnyDoc): PaymentBundlesOut {
  return {
    id: docId(doc),
    amount: numOrNull(doc.amount),
    numberOfstars: numOrNull(doc.numberOfstars),
    bundleType: normalizeBundleType(doc.bundleType),
    durationDays: numOrNull(doc.durationDays),
    description: String(doc.description ?? ""),
    dateCreated: toIsoOffset(doc.dateCreated),
  };
}

export function toPricingBundleOut(doc: AnyDoc): PricingBundleOut {
  return {
    id: docId(doc),
    bundleType: normalizeBundleType(doc.bundleType) ?? "cash",
    description: String(doc.description ?? ""),
    durationDays: numOrNull(doc.durationDays),
    cashAmount: numOrNull(doc.cashAmount ?? doc.amount),
    starAmount: numOrNull(doc.starAmount ?? doc.numberOfstars),
    dateCreated: toIsoOffset(doc.dateCreated),
  };
}

export function toTransactionOut(doc: AnyDoc): TransactionOut {
  return {
    id: docId(doc),
    userId: String(doc.userId ?? ""),
    paymentId: String(doc.paymentId ?? ""),
    numberOfStars: numOrDefault(doc.numberOfStars, 0),
    TransactionType: (strOrNull(doc.TransactionType) ?? "cash") as TransactionType,
    amount: numOrDefault(doc.amount, 0),
    dateCreated: toIsoOffset(doc.dateCreated) ?? nowIso(),
  };
}
