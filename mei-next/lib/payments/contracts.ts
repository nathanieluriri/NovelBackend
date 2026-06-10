/**
 * Payment provider contracts — port of `services/payments/contracts.py` +
 * the normalized DTOs from `schemas/payments_schema.py` (payments.md §2).
 *
 * The orchestrator holds a `Record<PaymentProvider, PaymentProviderAdapter>`
 * registry; each adapter normalizes its provider's checkout/webhook/verify
 * shapes into these DTOs.
 */
import { envInt } from "@/lib/env";
import type { CheckoutSessionOut, PaymentProvider } from "@/lib/serializers";

export type { BundleType, CheckoutSessionOut, PaymentProvider, PaymentStatus } from "@/lib/serializers";

/** Body of `POST /payment/checkout/create` (schema.md §5 CheckoutCreateRequest). */
export interface CheckoutCreateRequest {
  bundleId: string;
  /** 2-letter country code, uppercased upstream. */
  countryCode: string;
  provider?: PaymentProvider | null;
  chapterId?: string | null;
  successUrl?: string | null;
  cancelUrl?: string | null;
}

/** Orchestrator-resolved context handed to the adapter alongside the request. */
export interface CheckoutContext {
  /** Major-unit amount (bundle `amount`). Adapters convert to minor units as needed. */
  amount: number;
  currency: string;
  txRef: string;
  email: string;
  firstName?: string | null;
  lastName?: string | null;
}

export interface NormalizedWebhookEvent {
  provider: PaymentProvider;
  eventId: string;
  txRef?: string | null;
  providerReference?: string | null;
  /** Major-unit amount as reported by the webhook (informational only — never trusted). */
  amount?: number | null;
  currency?: string | null;
  status: string;
  raw: unknown;
}

export interface VerificationResult {
  verified: boolean;
  providerReference?: string | null;
  /** Major-unit amount re-fetched from the provider (the trusted value). */
  amount?: number | null;
  currency?: string | null;
  txRef?: string | null;
  reason?: string | null;
}

/**
 * TS port of the legacy `Protocol`. Webhook bodies arrive as the RAW request
 * text (`await req.text()`) — adapters must verify signatures against the
 * exact bytes before parsing.
 */
export interface PaymentProviderAdapter {
  createCheckoutSession(req: CheckoutCreateRequest, ctx: CheckoutContext): Promise<CheckoutSessionOut>;
  verifyWebhook(rawBody: string, headers: Record<string, string>): Promise<NormalizedWebhookEvent>;
  verifyTransaction(providerReference: string): Promise<VerificationResult>;
}

/** Legacy default redirect targets (stripe success/cancel, flutterwave redirect). */
export const DEFAULT_SUCCESS_URL = "https://nattyboi-novelbackend.hf.space/success";
export const DEFAULT_CANCEL_URL = "https://nattyboi-novelbackend.hf.space/cancel";

/** `PAYMENTS_PROVIDER_TIMEOUT_SECONDS` (default 10) → milliseconds. */
export function providerTimeoutMs(): number {
  return envInt("PAYMENTS_PROVIDER_TIMEOUT_SECONDS", 10) * 1000;
}
