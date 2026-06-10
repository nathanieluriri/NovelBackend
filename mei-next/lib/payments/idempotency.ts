/**
 * Webhook idempotency — port of `services/payments/idempotency.py` +
 * `repositories/payment_repo.py::register_webhook_event` (payments.md §8.1).
 *
 * One row per `(provider, eventId)` in `payment_webhook_events` (unique
 * index). A duplicate-key insert (Mongo error 11000) means the event was
 * already processed → return false and the orchestrator short-circuits with
 * `{status:"idempotent_replay"}` BEFORE any verify/fulfill work.
 */
import { db } from "@/lib/db";
import { WebhookEvent } from "@/lib/models";
import { nowIso } from "@/lib/util/dates";
import type { PaymentProvider } from "./contracts";

/** Mongo duplicate-key detection (raw MongoServerError or wrapped). */
export function isDuplicateKeyError(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  const e = err as { code?: unknown; cause?: { code?: unknown } | null };
  if (e.code === 11000) return true;
  return typeof e.cause === "object" && e.cause !== null && e.cause.code === 11000;
}

/**
 * Lazy once-per-process index creation, mirroring the legacy
 * `ensure_payment_runtime_indexes` once-flag (the schema declares the unique
 * `(provider, eventId)` index but `autoIndex` is off). Best-effort: a failure
 * resets the guard so the next call retries.
 */
let webhookIndexesReady: Promise<unknown> | null = null;
function ensureWebhookEventIndexes(): Promise<unknown> {
  if (!webhookIndexesReady) {
    webhookIndexesReady = WebhookEvent.createIndexes().catch((err: unknown) => {
      webhookIndexesReady = null;
      console.warn("payments: failed to ensure payment_webhook_events indexes", err);
    });
  }
  return webhookIndexesReady;
}

/**
 * Insert the webhook event record; returns false when this `(provider,
 * eventId)` pair was already recorded (duplicate key 11000).
 */
export async function markEventIfNew(
  provider: PaymentProvider,
  eventId: string,
  txRef?: string | null,
  providerReference?: string | null,
): Promise<boolean> {
  await db();
  await ensureWebhookEventIndexes();
  try {
    await WebhookEvent.create({
      provider,
      eventId,
      txRef: txRef ?? null,
      providerReference: providerReference ?? null,
      receivedAt: nowIso(),
    });
    return true;
  } catch (err) {
    if (isDuplicateKeyError(err)) return false;
    throw err;
  }
}
