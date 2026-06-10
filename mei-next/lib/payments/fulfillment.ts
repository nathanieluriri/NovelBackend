/**
 * Fulfillment engine — port of `services/payments/fulfillment.py` +
 * the `create_transaction` core of `services/payment_service.py` +
 * `repositories/entitlement_repo.py` (payments.md §4, §8).
 *
 * Dispatch on bundleType:
 * - subscription / subscriptionCash → recordSubscriptionPurchase (stacks
 *   `expiresAt = max(now, current) + durationDays`).
 * - subscriptionStars → rejected in cash fulfillment (400).
 * - purchaseOfBooks → chapter entitlement (source "cash_checkout") + unread
 *   read record when newly created.
 * - default (cash / cashPromo / …) → recordPurchaseOfStars (wallet credit,
 *   idempotent by `Transaction.paymentId == txRef`).
 */
import { isValidObjectId } from "mongoose";
import { db } from "@/lib/db";
import { envBool } from "@/lib/env";
import { HttpError } from "@/lib/http/errors";
import {
  Entitlement,
  ReadRecord,
  Transaction,
  User,
  type EntitlementDoc,
  type PaymentBundleDoc,
  type UserDoc,
} from "@/lib/models";
import { toUserOut, type TransactionType, type UserOut } from "@/lib/serializers";
import { isChapterUnlocked } from "@/lib/services/access";
import { nowEpoch, nowIso, toIsoOffset } from "@/lib/util/dates";
import { getPaymentBundle, normalizeBundleType, SUBSCRIPTION_CASH_TYPES } from "./bundles";
import { isDuplicateKeyError } from "./idempotency";

/** Loose bundle doc alias (pinned seam uses `BundleDoc`). */
export type BundleDoc = PaymentBundleDoc;

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/** Port of `get_user_by_userId` — invalid ObjectId behaves like "not found". */
export async function findUserById(userId: string): Promise<UserDoc | null> {
  await db();
  if (!isValidObjectId(userId)) return null;
  return User.findById(userId).lean<UserDoc>();
}

/** Lazy once-per-process unique `(userId, chapterId)` index (legacy ensure_entitlement_indexes). */
let entitlementIndexesReady: Promise<unknown> | null = null;
function ensureEntitlementIndexes(): Promise<unknown> {
  if (!entitlementIndexesReady) {
    entitlementIndexesReady = Entitlement.createIndexes().catch((err: unknown) => {
      entitlementIndexesReady = null;
      console.warn("payments: failed to ensure entitlements indexes", err);
    });
  }
  return entitlementIndexesReady;
}

/**
 * Port of `create_chapter_entitlement_if_absent` — returns the existing row
 * with `created:false`, or inserts and returns `created:true`. Races on the
 * unique index resolve to the surviving row (idempotency layer 4).
 * `ENTITLEMENTS_WRITE_ENABLED=false` is the ops kill-switch (improvements.md).
 */
export async function createChapterEntitlementIfAbsent(
  userId: string,
  chapterId: string,
  source = "stars_wallet",
  txRef?: string | null,
): Promise<{ entitlement: EntitlementDoc; created: boolean }> {
  await db();
  await ensureEntitlementIndexes();

  const existing = await Entitlement.findOne({ userId, chapterId }).lean<EntitlementDoc>();
  if (existing) return { entitlement: existing, created: false };

  if (!envBool("ENTITLEMENTS_WRITE_ENABLED", true)) {
    throw new HttpError(503, "Entitlement writes are disabled");
  }

  try {
    const created = await Entitlement.create({
      userId,
      chapterId,
      grantType: "chapter_unlock",
      source,
      txRef: txRef ?? null,
      createdAt: nowIso(),
    });
    return { entitlement: created.toObject(), created: true };
  } catch (err) {
    if (isDuplicateKeyError(err)) {
      const winner = await Entitlement.findOne({ userId, chapterId }).lean<EntitlementDoc>();
      if (winner) return { entitlement: winner, created: false };
    }
    throw err;
  }
}

/** Port of `upsert_read_record(MarkAsRead(hasRead=False))` — the unread read row. */
async function upsertUnreadReadRecord(userId: string, chapterId: string): Promise<void> {
  await db();
  await ReadRecord.updateOne(
    { userId, chapterId },
    {
      $set: { userId, chapterId, hasRead: false },
      $currentDate: { lastUpdated: true },
      $setOnInsert: { dateCreated: nowIso() },
    },
    { upsert: true },
  );
}

function parseDateMs(value: unknown): number | null {
  if (typeof value !== "string" || !value) return null;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? null : ms;
}

/**
 * Port of `_update_subscription`: expiresAt = max(now, current expiresAt) +
 * durationDays — subscriptions STACK, never overwrite. Returns the refreshed
 * UserOut wire shape.
 */
export async function extendUserSubscription(userId: string, durationDays: number): Promise<UserOut> {
  await db();
  const user = await findUserById(userId);
  if (!user) throw new HttpError(404, "User not found");

  const nowMs = Date.now();
  const sub = (user.subscription ?? {}) as Record<string, unknown>;
  const currentExpiresMs = parseDateMs(sub.expiresAt);
  const baseMs = currentExpiresMs !== null && currentExpiresMs > nowMs ? currentExpiresMs : nowMs;
  const newExpiresAt = new Date(baseMs + durationDays * 24 * 60 * 60 * 1000);

  await User.updateOne(
    { _id: user._id },
    { $set: { subscription: { active: true, expiresAt: toIsoOffset(newExpiresAt) } } },
  );

  const refreshed = await findUserById(userId);
  return toUserOut(refreshed ?? user);
}

// ---------------------------------------------------------------------------
// create_transaction port (the wallet/transaction core of payment_service.py)
// ---------------------------------------------------------------------------

export interface CreateTransactionArgs {
  userId: string;
  bundleId: string;
  txRef?: string | null;
  chapterId?: string | null;
  txType: TransactionType;
}

/**
 * Exact port of `payment_service.create_transaction` — including the legacy
 * quirks: the chapter branch returns the user fetched BEFORE the balance
 * deduction, and an unknown txType (or a cash txType with a missing bundle)
 * falls through to 400 "Unsupported transaction type".
 */
export async function createTransaction(args: CreateTransactionArgs): Promise<UserOut> {
  await db();
  const { userId, bundleId, chapterId } = args;
  const txRef = args.txRef ?? null;
  const epoch = nowEpoch();

  if (args.txType === "transferOfStarCurrencyForChapterAccess") {
    if (!chapterId) throw new HttpError(400, "chapterId is required for chapter purchase");

    const bundle = await getPaymentBundle(bundleId);
    if (!bundle) throw new HttpError(404, "Payment bundle not found");
    if (normalizeBundleType(bundle.bundleType) !== "purchaseOfBooks") {
      throw new HttpError(400, "Invalid bundle type for chapter purchase");
    }
    if (bundle.numberOfstars === null || bundle.numberOfstars === undefined) {
      throw new HttpError(400, "Payment bundle missing stars");
    }
    const stars = Number(bundle.numberOfstars);

    const user = await findUserById(userId);
    if (!user) throw new HttpError(404, "User not found");

    const alreadyUnlocked = await isChapterUnlocked(user, chapterId);
    if (alreadyUnlocked) return toUserOut(user);

    const balance = Number(user.balance ?? 0);
    if (balance >= stars) {
      const chapterTxRef = txRef || `uid:${userId}||cid:${chapterId}||nos:${stars}||ts:${epoch}`;
      const { created } = await createChapterEntitlementIfAbsent(userId, chapterId, "stars_wallet", chapterTxRef);
      if (created) await upsertUnreadReadRecord(userId, chapterId);
      // Legacy quirk: the returned user is fetched BEFORE the deduction below.
      const refreshed = await findUserById(userId);
      const result = toUserOut(refreshed ?? user);
      if (created) {
        await Transaction.create({
          userId,
          paymentId: chapterTxRef,
          TransactionType: args.txType,
          numberOfStars: stars,
          amount: bundle.amount ?? null,
          dateCreated: nowIso(),
        });
        await User.updateOne({ _id: user._id }, { $inc: { balance: -stars } });
      }
      return result;
    }
    throw new HttpError(400, "Insufficient balance");
  }

  if (args.txType === "cash") {
    const bundle = await getPaymentBundle(bundleId);
    if (bundle) {
      if (bundle.amount === null || bundle.amount === undefined || Number(bundle.amount) <= 0) {
        throw new HttpError(400, "Cash bundle is missing amount");
      }
      const existing = await Transaction.findOne({ paymentId: txRef }).lean();
      if (!existing) {
        if (bundle.numberOfstars === null || bundle.numberOfstars === undefined) {
          throw new HttpError(400, "Payment bundle missing stars");
        }
        await Transaction.create({
          userId,
          paymentId: txRef,
          TransactionType: "cash",
          numberOfStars: bundle.numberOfstars,
          amount: bundle.amount,
          dateCreated: nowIso(),
        });
        if (isValidObjectId(userId)) {
          await User.updateOne({ _id: userId }, { $inc: { balance: Number(bundle.numberOfstars) } });
        }
      }
      const user = await findUserById(userId);
      if (!user) throw new HttpError(404, "User not found");
      return toUserOut(user);
    }
    // Legacy quirk: a missing bundle here falls through to the trailing 400.
  } else if (args.txType === "subscriptionPurchase") {
    const bundle = await getPaymentBundle(bundleId);
    if (
      !bundle ||
      bundle.durationDays === null ||
      bundle.durationDays === undefined ||
      !(SUBSCRIPTION_CASH_TYPES as readonly string[]).includes(String(bundle.bundleType)) ||
      bundle.amount === null ||
      bundle.amount === undefined ||
      Number(bundle.amount) <= 0
    ) {
      throw new HttpError(400, "Subscription bundle is invalid");
    }
    const existing = await Transaction.findOne({ paymentId: txRef }).lean();
    if (!existing) {
      await Transaction.create({
        userId,
        paymentId: txRef,
        TransactionType: "subscriptionPurchase",
        numberOfStars: 0,
        amount: bundle.amount,
        dateCreated: nowIso(),
      });
      return extendUserSubscription(userId, Number(bundle.durationDays));
    }
    const user = await findUserById(userId);
    if (!user) throw new HttpError(404, "User not found");
    return toUserOut(user);
  }

  throw new HttpError(400, "Unsupported transaction type");
}

/** Port of `record_purchase_of_stars` — wallet credit, idempotent by paymentId. */
export async function recordPurchaseOfStars(userId: string, txRef: string, bundleId: string): Promise<UserOut> {
  return createTransaction({ userId, bundleId, txRef, txType: "cash" });
}

/**
 * Port of `record_subscription_purchase` — pinned seam signature takes the
 * loaded bundle doc (CONVENTIONS.md); the transaction core re-validates it.
 */
export async function recordSubscriptionPurchase(
  userId: string,
  bundle: BundleDoc,
  txRef: string,
): Promise<UserOut> {
  const bundleId = String(bundle._id ?? bundle.id ?? "");
  return createTransaction({ userId, bundleId, txRef, txType: "subscriptionPurchase" });
}

// ---------------------------------------------------------------------------
// Cash fulfillment dispatch (payments.md §4)
// ---------------------------------------------------------------------------

export interface FulfillmentArgs {
  userId: string;
  bundleId: string;
  txRef: string;
  chapterId?: string | null;
}

/** Port of `fulfill_verified_payment` — dispatch on bundleType. */
export async function fulfillVerifiedPayment(args: FulfillmentArgs): Promise<Record<string, unknown>> {
  await db();
  const bundle = await getPaymentBundle(args.bundleId);
  if (!bundle) throw new HttpError(404, "Payment bundle not found");

  const bundleType = normalizeBundleType(bundle.bundleType);

  if (bundleType === "subscriptionCash") {
    const userOut = await recordSubscriptionPurchase(args.userId, bundle, args.txRef);
    return { grantType: "subscription", userId: userOut.userId };
  }

  if (bundleType === "subscriptionStars") {
    throw new HttpError(400, "Stars subscriptions must be purchased from wallet");
  }

  if (bundleType === "purchaseOfBooks") {
    if (!args.chapterId) throw new HttpError(400, "chapterId is required for chapter unlock");
    const { created } = await createChapterEntitlementIfAbsent(
      args.userId,
      args.chapterId,
      "cash_checkout",
      args.txRef,
    );
    if (created) await upsertUnreadReadRecord(args.userId, args.chapterId);
    return { grantType: "chapter_unlock", chapterId: args.chapterId, created };
  }

  const userOut = await recordPurchaseOfStars(args.userId, args.txRef, args.bundleId);
  return { grantType: "wallet_credit", userId: userOut.userId };
}
