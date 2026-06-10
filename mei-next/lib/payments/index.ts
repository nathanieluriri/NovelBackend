/**
 * @/lib/payments barrel — pinned seam (CONVENTIONS.md) plus the stars-wallet
 * purchases ported from `services/payment_service.py` (`pay_for_chapter`,
 * `purchase_subscription_with_stars`) — payments.md §5. Stars purchases
 * bypass providers entirely and operate on `users.balance`.
 */
import { isValidObjectId } from "mongoose";
import { db } from "@/lib/db";
import { HttpError } from "@/lib/http/errors";
import { Chapter, Transaction, User, type ChapterDoc, type UserDoc } from "@/lib/models";
import { resolveChapterAccessType } from "@/lib/services/access";
import { nowEpoch, nowIso } from "@/lib/util/dates";
import { getPaymentBundle, normalizeBundleType } from "./bundles";
import { createTransaction, extendUserSubscription, findUserById } from "./fulfillment";

// --- Pinned seam + service re-exports --------------------------------------

export { createCheckout, processWebhook } from "./orchestrator";
export {
  countBundles,
  createBundle,
  deleteBundle,
  getPaymentBundle,
  getPricingCatalog,
  listBundles,
  normalizeBundleType,
  updateBundle,
  SUBSCRIPTION_CASH_TYPES,
  SUBSCRIPTION_STAR_TYPES,
  type PaymentBundleCreateInput,
  type PaymentBundleUpdateInput,
} from "./bundles";
export {
  createChapterEntitlementIfAbsent,
  createTransaction,
  extendUserSubscription,
  findUserById,
  fulfillVerifiedPayment,
  recordPurchaseOfStars,
  recordSubscriptionPurchase,
  type BundleDoc,
  type CreateTransactionArgs,
  type FulfillmentArgs,
} from "./fulfillment";
export { markEventIfNew } from "./idempotency";
export { resolveCurrency, resolveProvider } from "./routing";
export {
  DEFAULT_CANCEL_URL,
  DEFAULT_SUCCESS_URL,
  providerTimeoutMs,
  type BundleType,
  type CheckoutContext,
  type CheckoutCreateRequest,
  type CheckoutSessionOut,
  type NormalizedWebhookEvent,
  type PaymentProvider,
  type PaymentProviderAdapter,
  type PaymentStatus,
  type VerificationResult,
} from "./contracts";

// --- Stars (wallet) purchases — payments.md §5 ------------------------------

/**
 * Port of `pay_for_chapter` (POST /payment/pay-chapter):
 * - chapter must resolve to accessType "paid" (else 409);
 * - chapter.unlockBundleId, when set, must match the requested bundle (400);
 * - then the chapter-purchase transaction core: bundle must be
 *   purchaseOfBooks with stars, balance >= numberOfstars, entitlement
 *   (source "stars_wallet") + unread read record, transaction dedup,
 *   `$inc balance -numberOfstars`.
 *
 * `chapterId` is a trailing param (the legacy body is `{bundle_id, chapterId}`);
 * missing → the legacy 400 "chapterId is required for chapter purchase".
 */
export async function payForChapterWithStars(
  user: UserDoc,
  bundleId: string,
  chapterId?: string | null,
): Promise<unknown> {
  await db();
  if (!chapterId) throw new HttpError(400, "chapterId is required for chapter purchase");

  const userId = String(user?._id ?? user?.userId ?? "");

  const chapter = isValidObjectId(chapterId)
    ? await Chapter.findById(chapterId).lean<ChapterDoc>()
    : null;
  if (!chapter) throw new HttpError(404, "Chapter not found");

  if (resolveChapterAccessType(chapter) !== "paid") {
    throw new HttpError(409, "Chapter does not require paid unlock");
  }
  if (chapter.unlockBundleId && String(chapter.unlockBundleId) !== bundleId) {
    throw new HttpError(400, "Invalid bundle for chapter unlock");
  }

  return createTransaction({
    userId,
    bundleId,
    chapterId,
    txType: "transferOfStarCurrencyForChapterAccess",
  });
}

/**
 * Port of `purchase_subscription_with_stars` (POST /payment/subscribe-with-stars):
 * validate the subscriptionStars bundle, balance check, record the
 * transaction, subtract stars, then stack the subscription window.
 */
export async function purchaseSubscriptionWithStars(user: UserDoc, bundleId: string): Promise<unknown> {
  await db();

  const bundle = await getPaymentBundle(bundleId);
  const bundleType = bundle ? normalizeBundleType(bundle.bundleType) : null;
  if (
    !bundle ||
    bundleType !== "subscriptionStars" ||
    bundle.numberOfstars === null ||
    bundle.numberOfstars === undefined ||
    Number(bundle.numberOfstars) <= 0 ||
    bundle.durationDays === null ||
    bundle.durationDays === undefined ||
    Number(bundle.durationDays) <= 0
  ) {
    throw new HttpError(400, "Subscription stars bundle is invalid");
  }
  const stars = Number(bundle.numberOfstars);

  const userId = String(user?._id ?? user?.userId ?? "");
  const fresh = await findUserById(userId);
  if (!fresh) throw new HttpError(404, "User not found");

  const balance = fresh.balance;
  if (balance === null || balance === undefined || Number(balance) < stars) {
    throw new HttpError(400, "Insufficient balance");
  }

  const txRef = `uid:${userId}||bid:${bundleId}||nos:${stars}||ts:${nowEpoch()}`;
  await Transaction.create({
    userId,
    paymentId: txRef,
    TransactionType: "subscriptionPurchase",
    numberOfStars: stars,
    amount: bundle.amount ?? 0,
    dateCreated: nowIso(),
  });
  await User.updateOne({ _id: fresh._id }, { $inc: { balance: -stars } });

  return extendUserSubscription(userId, Number(bundle.durationDays));
}
