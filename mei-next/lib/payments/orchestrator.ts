/**
 * Cash-payment orchestrator — port of `services/payments/orchestrator.py`
 * (payments.md §3): initiate → webhook → idempotency → server-side re-verify
 * → amount/currency assert → fulfill.
 *
 * Status lifecycle on `payment_runtime`: initiated → pending → verified →
 * fulfilled (or → failed). Every transition writes `updatedAt = nowIso()`.
 */
import { db } from "@/lib/db";
import { envBool } from "@/lib/env";
import { HttpError } from "@/lib/http/errors";
import { PaymentRuntime, type PaymentRuntimeDoc, type UserDoc } from "@/lib/models";
import { nowEpoch, nowIso } from "@/lib/util/dates";
import { getPaymentBundle, normalizeBundleType } from "./bundles";
import type {
  CheckoutCreateRequest,
  CheckoutSessionOut,
  NormalizedWebhookEvent,
  PaymentProvider,
  PaymentProviderAdapter,
  PaymentStatus,
} from "./contracts";
import { fulfillVerifiedPayment } from "./fulfillment";
import { markEventIfNew } from "./idempotency";
import { flutterwaveProvider } from "./providers/flutterwave";
import { paystackProvider } from "./providers/paystack";
import { stripeProvider } from "./providers/stripe";
import { resolveCurrency, resolveProvider } from "./routing";

const providerRegistry: Record<PaymentProvider, PaymentProviderAdapter> = {
  flutterwave: flutterwaveProvider,
  paystack: paystackProvider,
  stripe: stripeProvider,
};

/** Ops kill-switch (improvements.md) — declared-but-unused in legacy, real here. */
function assertOrchestratorEnabled(): void {
  if (!envBool("PAYMENTS_ORCHESTRATOR_ENABLED", true)) {
    throw new HttpError(503, "Payments orchestrator is disabled");
  }
}

/** Lazy once-per-process runtime indexes (unique txRef + sparse provider/ref). */
let runtimeIndexesReady: Promise<unknown> | null = null;
function ensureRuntimeIndexes(): Promise<unknown> {
  if (!runtimeIndexesReady) {
    runtimeIndexesReady = PaymentRuntime.createIndexes().catch((err: unknown) => {
      runtimeIndexesReady = null;
      console.warn("payments: failed to ensure payment_runtime indexes", err);
    });
  }
  return runtimeIndexesReady;
}

function buildTxRef(userId: string, bundleId: string): string {
  return `uid:${userId}|ts:${nowEpoch()}|bid:${bundleId}`;
}

/** Status transition on payment_runtime — always bumps `updatedAt`. */
async function updateRuntimeStatus(
  txRef: string,
  status: PaymentStatus,
  providerReference?: string | null,
): Promise<void> {
  await db();
  const set: Record<string, unknown> = { status, updatedAt: nowIso() };
  if (providerReference) set.providerReference = providerReference;
  await PaymentRuntime.updateOne({ txRef }, { $set: set });
}

// ---------------------------------------------------------------------------
// 3A. Create checkout
// ---------------------------------------------------------------------------

/**
 * Port of `create_checkout`:
 * 1. bundle 404; reject subscriptionStars (wallet endpoint) and amount <= 0.
 * 2. resolve provider/currency by countryCode.
 * 3. txRef = "uid:{userId}|ts:{epochSeconds}|bid:{bundleId}".
 * 4. adapter checkout session; insert payment_runtime (status "pending").
 */
export async function createCheckout(user: UserDoc, body: CheckoutCreateRequest): Promise<CheckoutSessionOut> {
  assertOrchestratorEnabled();
  await db();

  const userId = String(user?._id ?? user?.userId ?? "");

  const bundle = await getPaymentBundle(body.bundleId);
  if (!bundle) throw new HttpError(404, "Payment bundle not found");
  if (normalizeBundleType(bundle.bundleType) === "subscriptionStars") {
    throw new HttpError(400, "Use wallet endpoint for stars subscription purchase");
  }
  if (bundle.amount === null || bundle.amount === undefined || Number(bundle.amount) <= 0) {
    throw new HttpError(400, "Checkout requires a cash-priced bundle");
  }

  const provider = resolveProvider(body.countryCode, body.provider ?? null);
  const currency = resolveCurrency(body.countryCode);
  const txRef = buildTxRef(userId, body.bundleId);
  const amount = Number(bundle.amount);

  const adapter = providerRegistry[provider];
  const session = await adapter.createCheckoutSession(body, {
    amount,
    currency,
    txRef,
    email: String(user?.email ?? ""),
    firstName: user?.firstName ?? null,
    lastName: user?.lastName ?? null,
  });

  await ensureRuntimeIndexes();
  const now = nowIso();
  await PaymentRuntime.create({
    txRef,
    userId,
    bundleId: body.bundleId,
    chapterId: body.chapterId ?? null,
    provider,
    providerReference: session.providerReference,
    countryCode: body.countryCode.toUpperCase(),
    currency,
    amount,
    status: "pending",
    createdAt: now,
    updatedAt: now,
  });

  return session;
}

// ---------------------------------------------------------------------------
// 3B. Process webhook
// ---------------------------------------------------------------------------

/**
 * Port of `process_webhook`:
 * 1. adapter signature verification on the RAW body.
 * 2. idempotency insert — duplicate → {status:"idempotent_replay"} and stop.
 * 3. txRef required (400); runtime by txRef (404); providerRef (400).
 * 4. server-side re-verify (never trust webhook amounts) — unverified →
 *    runtime "failed" + 400.
 * 5. amount tolerance 0.0001 and uppercase currency match — else "failed" + 400.
 * 6. runtime "verified" → fulfill → runtime "fulfilled".
 */
export async function processWebhook(
  provider: PaymentProvider,
  rawBody: string,
  headers: Record<string, string>,
): Promise<unknown> {
  assertOrchestratorEnabled();

  const adapter = providerRegistry[provider];
  const lowered: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) lowered[key.toLowerCase()] = value;

  const event: NormalizedWebhookEvent = await adapter.verifyWebhook(rawBody, lowered);

  await db();
  const isNew = await markEventIfNew(
    provider,
    event.eventId,
    event.txRef ?? null,
    event.providerReference ?? null,
  );
  if (!isNew) return { status: "idempotent_replay" };

  if (!event.txRef) throw new HttpError(400, "Missing txRef in webhook event");

  await ensureRuntimeIndexes();
  const runtime = await PaymentRuntime.findOne({ txRef: event.txRef }).lean<PaymentRuntimeDoc>();
  if (!runtime) throw new HttpError(404, "Payment runtime not found");

  const providerRef = event.providerReference || runtime.providerReference;
  if (!providerRef) throw new HttpError(400, "Missing provider reference");
  const providerRefStr = String(providerRef);

  const verification = await adapter.verifyTransaction(providerRefStr);
  if (!verification.verified) {
    await updateRuntimeStatus(String(runtime.txRef), "failed");
    throw new HttpError(400, verification.reason || "Verification failed");
  }

  const expectedAmount = Number(runtime.amount);
  if (
    verification.amount === null ||
    verification.amount === undefined ||
    Math.abs(Number(verification.amount) - expectedAmount) > 0.0001
  ) {
    await updateRuntimeStatus(String(runtime.txRef), "failed");
    throw new HttpError(400, "Amount mismatch during verification");
  }

  const expectedCurrency = String(runtime.currency ?? "").toUpperCase();
  const verifiedCurrency = (verification.currency ?? "").toUpperCase();
  if (!verifiedCurrency || verifiedCurrency !== expectedCurrency) {
    await updateRuntimeStatus(String(runtime.txRef), "failed");
    throw new HttpError(400, "Currency mismatch during verification");
  }

  await updateRuntimeStatus(String(runtime.txRef), "verified", providerRefStr);

  const fulfillment = await fulfillVerifiedPayment({
    userId: String(runtime.userId),
    bundleId: String(runtime.bundleId),
    txRef: String(runtime.txRef),
    chapterId: runtime.chapterId ?? null,
  });

  await updateRuntimeStatus(String(runtime.txRef), "fulfilled", providerRefStr);

  return {
    status: "fulfilled",
    txRef: runtime.txRef,
    provider,
    fulfillment,
  };
}
