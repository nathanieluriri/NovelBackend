/**
 * Bundle catalog service — port of the bundle half of
 * `repositories/payment_repo.py`, the `PaymentBundles(Update)` validators in
 * `schemas/payments_schema.py` (`validate_for_bundle_type`), and
 * `services/payment_service.py::get_pricing_catalog` (payments.md §6,
 * schema.md §5 PaymentBundles rules).
 *
 * Bundles live in the legacy `payments` collection. No hardcoded tiers —
 * everything is data-driven and admin-managed.
 */
import { isValidObjectId } from "mongoose";
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { PaymentBundle, type PaymentBundleDoc } from "@/lib/models";
import {
  toPaymentBundlesOut,
  toPricingBundleOut,
  type BundleType,
  type PaymentBundlesOut,
  type PricingBundleOut,
  type PricingCatalogOut,
} from "@/lib/serializers";
import { nowEpoch } from "@/lib/util/dates";

/** Legacy SUBSCRIPTION_CASH_TYPES — "subscription" is the pre-normalization alias. */
export const SUBSCRIPTION_CASH_TYPES: readonly BundleType[] = ["subscription", "subscriptionCash"];
export const SUBSCRIPTION_STAR_TYPES: readonly BundleType[] = ["subscriptionStars"];

const ALL_BUNDLE_TYPES: readonly BundleType[] = [
  "cash",
  "purchaseOfBooks",
  "transferringStarsToOtherUsers",
  "cashPromo",
  "bookPromo",
  "subscription",
  "subscriptionCash",
  "subscriptionStars",
];

/** Legacy quirk: bundleType "subscription" normalizes to "subscriptionCash" on read/write. */
export function normalizeBundleType(raw: unknown): BundleType | null {
  if (raw === null || raw === undefined) return null;
  const value = String(raw);
  if (value === "subscription") return "subscriptionCash";
  return (ALL_BUNDLE_TYPES as readonly string[]).includes(value) ? (value as BundleType) : null;
}

/** Port of `get_payment_bundle` — invalid ObjectId behaves like "not found". */
export async function getPaymentBundle(bundleId: string): Promise<PaymentBundleDoc | null> {
  await db();
  if (!isValidObjectId(bundleId)) return null;
  return PaymentBundle.findById(bundleId).lean<PaymentBundleDoc>();
}

// ---------------------------------------------------------------------------
// Admin CRUD
// ---------------------------------------------------------------------------

export interface PaymentBundleCreateInput {
  bundleType: BundleType;
  amount?: number | null;
  numberOfstars?: number | null;
  durationDays?: number | null;
  description: string;
  features?: string[] | null;
}

export interface PaymentBundleUpdateInput {
  amount?: number | null;
  bundleType?: BundleType | null;
  numberOfstars?: number | null;
  durationDays?: number | null;
  description?: string | null;
  features?: string[] | null;
}

/** Pydantic-style 422 (after-validator ValueError → "Value error, <msg>"). */
function validationError(message: string): HttpError {
  return new HttpError(422, "Validation failed", [
    { type: "value_error", loc: ["body"], msg: `Value error, ${message}`, input: null },
  ]);
}

/** Shared non-negative checks (PaymentBundles + PaymentBundlesUpdate). */
function validateCommonFields(input: {
  amount?: number | null;
  numberOfstars?: number | null;
  durationDays?: number | null;
}): void {
  if (input.amount !== null && input.amount !== undefined && input.amount < 0) {
    throw validationError("amount cannot be negative");
  }
  if (input.numberOfstars !== null && input.numberOfstars !== undefined && input.numberOfstars < 0) {
    throw validationError("numberOfstars cannot be negative");
  }
  if (input.durationDays !== null && input.durationDays !== undefined && input.durationDays <= 0) {
    throw validationError("durationDays must be greater than 0");
  }
}

/** Exact port of `PaymentBundles.validate_for_bundle_type`. */
function validateForBundleType(input: PaymentBundleCreateInput): void {
  validateCommonFields(input);
  const { bundleType } = input;
  const amount = input.amount ?? null;
  const numberOfstars = input.numberOfstars ?? null;
  const durationDays = input.durationDays ?? null;

  if (SUBSCRIPTION_CASH_TYPES.includes(bundleType)) {
    if (amount === null || amount <= 0) {
      throw validationError("Cash subscription bundle requires amount > 0");
    }
    if (durationDays === null || durationDays <= 0) {
      throw validationError("Cash subscription bundle requires durationDays > 0");
    }
    if (numberOfstars !== null && numberOfstars !== 0) {
      throw validationError("Cash subscription bundle must not set numberOfstars");
    }
    return;
  }

  if (SUBSCRIPTION_STAR_TYPES.includes(bundleType)) {
    if (numberOfstars === null || numberOfstars <= 0) {
      throw validationError("Stars subscription bundle requires numberOfstars > 0");
    }
    if (durationDays === null || durationDays <= 0) {
      throw validationError("Stars subscription bundle requires durationDays > 0");
    }
    if (amount !== null && amount !== 0) {
      throw validationError("Stars subscription bundle must not set amount");
    }
    return;
  }

  if (amount === null || amount <= 0) {
    throw validationError("amount must be greater than 0");
  }

  if (bundleType === "cash" || bundleType === "purchaseOfBooks") {
    if (numberOfstars === null || numberOfstars <= 0) {
      throw validationError("numberOfstars must be greater than 0 for this bundle type");
    }
  }
}

/**
 * Port of `create_payment_bundle`: legacy "subscription" → "subscriptionCash",
 * full per-type validation, `dateCreated` stored as epoch seconds,
 * None-valued fields excluded (pydantic `exclude_none`).
 */
export async function createBundle(input: PaymentBundleCreateInput): Promise<PaymentBundlesOut> {
  const bundleType = input.bundleType === "subscription" ? "subscriptionCash" : input.bundleType;
  const normalized: PaymentBundleCreateInput = { ...input, bundleType };
  validateForBundleType(normalized);

  await db();
  const fields: Record<string, unknown> = {
    bundleType: normalized.bundleType,
    description: normalized.description,
  };
  if (normalized.amount !== null && normalized.amount !== undefined) fields.amount = normalized.amount;
  if (normalized.numberOfstars !== null && normalized.numberOfstars !== undefined) {
    fields.numberOfstars = normalized.numberOfstars;
  }
  if (normalized.durationDays !== null && normalized.durationDays !== undefined) {
    fields.durationDays = normalized.durationDays;
  }
  if (normalized.features !== null && normalized.features !== undefined) {
    fields.features = normalized.features;
  }
  fields.dateCreated = nowEpoch();

  const created = await PaymentBundle.create(fields);
  return toPaymentBundlesOut(created.toObject());
}

/**
 * Port of `update_payment_bundle` (+ `PaymentBundlesUpdate` validators):
 * partial $set of non-null fields, `dateUpdated` epoch seconds, returns
 * whether a document was actually modified. Empty patch → false (legacy).
 */
export async function updateBundle(bundleId: string, input: PaymentBundleUpdateInput): Promise<boolean> {
  const bundleType = input.bundleType === "subscription" ? "subscriptionCash" : input.bundleType;
  const normalized: PaymentBundleUpdateInput = { ...input, bundleType };
  validateCommonFields(normalized);

  await db();
  if (!isValidObjectId(bundleId)) return false;

  const partial: Record<string, unknown> = {};
  if (normalized.amount !== null && normalized.amount !== undefined) partial.amount = normalized.amount;
  if (normalized.bundleType !== null && normalized.bundleType !== undefined) {
    partial.bundleType = normalized.bundleType;
  }
  if (normalized.numberOfstars !== null && normalized.numberOfstars !== undefined) {
    partial.numberOfstars = normalized.numberOfstars;
  }
  if (normalized.durationDays !== null && normalized.durationDays !== undefined) {
    partial.durationDays = normalized.durationDays;
  }
  if (normalized.description !== null && normalized.description !== undefined) {
    partial.description = normalized.description;
  }
  if (normalized.features !== null && normalized.features !== undefined) {
    partial.features = normalized.features;
  }
  if (Object.keys(partial).length === 0) return false;
  partial.dateUpdated = nowEpoch();

  const result = await PaymentBundle.updateOne({ _id: bundleId }, { $set: partial });
  return result.modifiedCount > 0;
}

/** Port of `delete_payment_bundle` — false when missing/invalid id. */
export async function deleteBundle(bundleId: string): Promise<boolean> {
  await db();
  if (!isValidObjectId(bundleId)) return false;
  const result = await PaymentBundle.deleteOne({ _id: bundleId });
  return result.deletedCount > 0;
}

/** Port of `get_all_payment_bundles(skip, limit)` — natural order, wire shapes. */
export async function listBundles(skip = 0, limit?: number | null): Promise<PaymentBundlesOut[]> {
  await db();
  let query = PaymentBundle.find({}).skip(skip);
  if (limit !== null && limit !== undefined) query = query.limit(limit);
  const docs = await query.lean<PaymentBundleDoc[]>();
  return docs.map((doc) => toPaymentBundlesOut(doc));
}

/** Port of `count_all_payment_bundles`. */
export async function countBundles(): Promise<number> {
  await db();
  return PaymentBundle.countDocuments({});
}

// ---------------------------------------------------------------------------
// Pricing catalog (payments.md §6)
// ---------------------------------------------------------------------------

/**
 * Groups all bundles:
 * - subscriptionPlans = subscription cash + stars
 * - starBundles       = cash (cash_to_star) + cashPromo
 * - chapterUnlockBundles = purchaseOfBooks (star_to_book)
 * Unknown/missing bundleType (and transfer/bookPromo types) are skipped.
 */
export async function getPricingCatalog(): Promise<PricingCatalogOut> {
  await db();
  const docs = await PaymentBundle.find({}).lean<PaymentBundleDoc[]>();

  const subscriptionPlans: PricingBundleOut[] = [];
  const starBundles: PricingBundleOut[] = [];
  const chapterUnlockBundles: PricingBundleOut[] = [];

  for (const doc of docs) {
    const bundleType = normalizeBundleType(doc.bundleType);
    if (bundleType === null) continue;
    const item = toPricingBundleOut(doc);
    if (bundleType === "subscriptionCash" || bundleType === "subscriptionStars") {
      subscriptionPlans.push(item);
      continue;
    }
    if (bundleType === "cash" || bundleType === "cashPromo") {
      starBundles.push(item);
      continue;
    }
    if (bundleType === "purchaseOfBooks") {
      chapterUnlockBundles.push(item);
    }
  }

  return { subscriptionPlans, starBundles, chapterUnlockBundles };
}
