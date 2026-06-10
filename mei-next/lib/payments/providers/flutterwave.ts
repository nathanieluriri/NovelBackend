/**
 * Flutterwave adapter — port of `services/payments/providers/flutterwave_provider.py`
 * (payments.md §2 per-provider table).
 * - Checkout: `POST /payments`, Bearer FLUTTERWAVE_SECRET_KEY, amount as a
 *   **string** (major units), url = data.link, ref = data.id. Always enabled.
 * - Webhook: `verif-hash` (or `verif_hash`) header compared against
 *   FLW_WEBHOOK_SECRET_HASH (static shared hash, timing-safe compare).
 * - Verify: `GET /transactions/{ref}/verify`; verified = status "successful".
 * - Timeout: PAYMENTS_PROVIDER_TIMEOUT_SECONDS (default 10) via AbortSignal.timeout.
 */
import { timingSafeEqual } from "node:crypto";
import { env } from "@/lib/env";
import { HttpError } from "@/lib/http/errors";
import type {
  CheckoutCreateRequest,
  CheckoutContext,
  CheckoutSessionOut,
  NormalizedWebhookEvent,
  PaymentProviderAdapter,
  VerificationResult,
} from "../contracts";
import { DEFAULT_SUCCESS_URL, providerTimeoutMs } from "../contracts";

const BASE_URL = "https://api.flutterwave.com/v3";

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a, "utf8");
  const bb = Buffer.from(b, "utf8");
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

async function flwFetch(path: string, init: RequestInit): Promise<Record<string, any>> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env("FLUTTERWAVE_SECRET_KEY") ?? ""}`,
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    signal: AbortSignal.timeout(providerTimeoutMs()),
  });
  if (!resp.ok) {
    // Legacy `raise_for_status()` surfaced as an unhandled 500 — keep that.
    throw new Error(`Flutterwave request failed: ${resp.status} ${await resp.text()}`);
  }
  return (await resp.json()) as Record<string, any>;
}

export const flutterwaveProvider: PaymentProviderAdapter = {
  async createCheckoutSession(
    req: CheckoutCreateRequest,
    ctx: CheckoutContext,
  ): Promise<CheckoutSessionOut> {
    const payload = {
      tx_ref: ctx.txRef,
      amount: `${ctx.amount}`, // major-unit STRING — flutterwave quirk
      currency: ctx.currency,
      redirect_url: req.successUrl || DEFAULT_SUCCESS_URL,
      customer: {
        email: ctx.email,
        name: `${ctx.firstName || "Stranger"} ${ctx.lastName || "Stranger"}`,
      },
      meta: {
        bundleId: req.bundleId,
        chapterId: req.chapterId ?? null,
        countryCode: req.countryCode,
      },
    };

    const body = await flwFetch("/payments", { method: "POST", body: JSON.stringify(payload) });
    const data: Record<string, any> = body.data ?? {};

    return {
      checkoutUrl: String(data.link ?? ""),
      provider: "flutterwave",
      providerReference: String(data.id ?? ""),
      txRef: ctx.txRef,
      status: "pending",
      expiresAt: null,
    };
  },

  async verifyWebhook(rawBody: string, headers: Record<string, string>): Promise<NormalizedWebhookEvent> {
    const headerHash = headers["verif-hash"] || headers["verif_hash"];
    const secret = env("FLW_WEBHOOK_SECRET_HASH") ?? "";
    if (!headerHash || !secret || !safeEqual(headerHash, secret)) {
      throw new HttpError(403, "Invalid flutterwave webhook signature");
    }

    const payload = JSON.parse(rawBody) as Record<string, any>;
    const data: Record<string, any> = payload.data ?? {};
    return {
      provider: "flutterwave",
      eventId: String(data.id ?? payload.event ?? "unknown"),
      txRef: data.tx_ref ?? null,
      providerReference: String(data.id ?? data.flw_ref ?? ""),
      amount: data.amount !== null && data.amount !== undefined ? Number(data.amount) : null,
      currency: data.currency ?? null,
      status: String(data.status ?? "unknown"),
      raw: payload,
    };
  },

  async verifyTransaction(providerReference: string): Promise<VerificationResult> {
    const body = await flwFetch(`/transactions/${providerReference}/verify`, { method: "GET" });
    const payload: Record<string, any> = body.data ?? {};

    return {
      verified: String(payload.status ?? "").toLowerCase() === "successful",
      providerReference: String(payload.id ?? providerReference),
      amount: payload.amount !== null && payload.amount !== undefined ? Number(payload.amount) : null,
      currency: payload.currency ?? null,
      txRef: payload.tx_ref ?? null,
    };
  },
};
