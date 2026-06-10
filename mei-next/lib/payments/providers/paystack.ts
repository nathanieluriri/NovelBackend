/**
 * Paystack adapter — port of `services/payments/providers/paystack_provider.py`
 * (payments.md §2 per-provider table).
 * - Checkout: `POST /transaction/initialize`, amount in kobo (*100),
 *   reference = txRef, url = data.authorization_url, ref = data.reference.
 * - Webhook: HMAC-SHA512 of the raw body keyed by PAYSTACK_WEBHOOK_SECRET,
 *   timing-safe compared against `x-paystack-signature`; amount = amount/100.
 * - Verify: `GET /transaction/verify/{ref}`; verified = status "success".
 * - `PAYSTACK_ENABLED` gate (503) on checkout creation only, like legacy.
 */
import { createHmac, timingSafeEqual } from "node:crypto";
import { env, envBool } from "@/lib/env";
import { HttpError } from "@/lib/http/errors";
import type {
  CheckoutCreateRequest,
  CheckoutContext,
  CheckoutSessionOut,
  NormalizedWebhookEvent,
  PaymentProviderAdapter,
  VerificationResult,
} from "../contracts";
import { providerTimeoutMs } from "../contracts";

const BASE_URL = "https://api.paystack.co";

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a, "utf8");
  const bb = Buffer.from(b, "utf8");
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

async function paystackFetch(path: string, init: RequestInit): Promise<Record<string, any>> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env("PAYSTACK_SECRET_KEY") ?? ""}`,
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    signal: AbortSignal.timeout(providerTimeoutMs()),
  });
  if (!resp.ok) {
    // Legacy `raise_for_status()` surfaced as an unhandled 500 — keep that.
    throw new Error(`Paystack request failed: ${resp.status} ${await resp.text()}`);
  }
  return (await resp.json()) as Record<string, any>;
}

export const paystackProvider: PaymentProviderAdapter = {
  async createCheckoutSession(
    req: CheckoutCreateRequest,
    ctx: CheckoutContext,
  ): Promise<CheckoutSessionOut> {
    if (!envBool("PAYSTACK_ENABLED", true)) {
      throw new HttpError(503, "Paystack is disabled");
    }

    const payload = {
      email: ctx.email,
      amount: Math.round(ctx.amount * 100), // kobo (minor units)
      currency: ctx.currency,
      reference: ctx.txRef,
      metadata: {
        bundleId: req.bundleId,
        chapterId: req.chapterId ?? null,
        countryCode: req.countryCode,
        firstName: ctx.firstName ?? null,
        lastName: ctx.lastName ?? null,
      },
      callback_url: req.successUrl ?? null,
    };

    const body = await paystackFetch("/transaction/initialize", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const data: Record<string, any> = body.data ?? {};

    return {
      checkoutUrl: String(data.authorization_url ?? ""),
      provider: "paystack",
      providerReference: String(data.reference ?? ctx.txRef),
      txRef: ctx.txRef,
      status: "pending",
      expiresAt: null,
    };
  },

  async verifyWebhook(rawBody: string, headers: Record<string, string>): Promise<NormalizedWebhookEvent> {
    const signature = headers["x-paystack-signature"];
    if (!signature) {
      throw new HttpError(403, "Missing paystack signature");
    }

    const computed = createHmac("sha512", env("PAYSTACK_WEBHOOK_SECRET") ?? "")
      .update(rawBody, "utf8")
      .digest("hex");
    if (!safeEqual(computed, signature)) {
      throw new HttpError(403, "Invalid paystack webhook signature");
    }

    const payload = JSON.parse(rawBody) as Record<string, any>;
    const data: Record<string, any> = payload.data ?? {};
    const amount = data.amount;
    return {
      provider: "paystack",
      eventId: String(data.id ?? payload.event ?? "unknown"),
      txRef: data.reference ?? null,
      providerReference: data.reference ?? null,
      amount: amount !== null && amount !== undefined ? Number(amount) / 100 : null,
      currency: data.currency ?? null,
      status: String(data.status ?? "unknown"),
      raw: payload,
    };
  },

  async verifyTransaction(providerReference: string): Promise<VerificationResult> {
    const body = await paystackFetch(`/transaction/verify/${providerReference}`, { method: "GET" });
    const payload: Record<string, any> = body.data ?? {};

    const amount = payload.amount;
    return {
      verified: String(payload.status ?? "").toLowerCase() === "success",
      providerReference: String(payload.reference ?? providerReference),
      amount: amount !== null && amount !== undefined ? Number(amount) / 100 : null,
      currency: payload.currency ?? null,
      txRef: payload.reference ?? null,
    };
  },
};
