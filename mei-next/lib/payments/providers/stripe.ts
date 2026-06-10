/**
 * Stripe adapter — port of `services/payments/providers/stripe_provider.py`
 * (payments.md §2 per-provider table).
 * - Checkout: `checkout.sessions.create(mode:"payment")`, minor units (*100),
 *   `client_reference_id = txRef`, metadata {bundleId, chapterId, countryCode}.
 * - Webhook: `stripe-signature` header → `webhooks.constructEvent(raw, sig, STRIPE_WEBHOOK_SECRET)`.
 * - Verify: `checkout.sessions.retrieve`; verified = payment_status === "paid".
 * - `STRIPE_ENABLED` gate (503) on checkout creation only, like legacy.
 */
import Stripe from "stripe";
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
import { DEFAULT_CANCEL_URL, DEFAULT_SUCCESS_URL, providerTimeoutMs } from "../contracts";

/** Lazy singleton — never construct the Stripe client at module scope. */
let cachedClient: Stripe | null = null;
function stripeClient(): Stripe {
  if (!cachedClient) {
    cachedClient = new Stripe(env("STRIPE_SECRET_KEY") ?? "", {
      timeout: providerTimeoutMs(),
    });
  }
  return cachedClient;
}

export const stripeProvider: PaymentProviderAdapter = {
  async createCheckoutSession(
    req: CheckoutCreateRequest,
    ctx: CheckoutContext,
  ): Promise<CheckoutSessionOut> {
    if (!envBool("STRIPE_ENABLED", true)) {
      throw new HttpError(503, "Stripe is disabled");
    }

    const session = await stripeClient().checkout.sessions.create({
      mode: "payment",
      success_url: req.successUrl || DEFAULT_SUCCESS_URL,
      cancel_url: req.cancelUrl || DEFAULT_CANCEL_URL,
      customer_email: ctx.email,
      client_reference_id: ctx.txRef,
      line_items: [
        {
          quantity: 1,
          price_data: {
            currency: ctx.currency.toLowerCase(),
            unit_amount: Math.round(ctx.amount * 100),
            product_data: { name: "Mei payment" },
          },
        },
      ],
      metadata: {
        bundleId: req.bundleId,
        chapterId: req.chapterId || "",
        countryCode: req.countryCode,
      },
    });

    return {
      checkoutUrl: session.url ?? "",
      provider: "stripe",
      providerReference: session.id,
      txRef: ctx.txRef,
      status: "pending",
      expiresAt: null,
    };
  },

  async verifyWebhook(rawBody: string, headers: Record<string, string>): Promise<NormalizedWebhookEvent> {
    const signature = headers["stripe-signature"];
    if (!signature) {
      throw new HttpError(403, "Missing stripe signature");
    }

    let event: Stripe.Event;
    try {
      event = stripeClient().webhooks.constructEvent(
        rawBody,
        signature,
        env("STRIPE_WEBHOOK_SECRET") ?? "",
      );
    } catch {
      throw new HttpError(403, "Invalid stripe webhook signature");
    }

    const payload = JSON.parse(rawBody) as Record<string, any>;
    const dataObj: Record<string, any> = payload?.data?.object ?? {};

    const amountTotal = dataObj.amount_total;
    return {
      provider: "stripe",
      eventId: event.id,
      txRef: dataObj.client_reference_id ?? null,
      providerReference: dataObj.id ?? null,
      amount: amountTotal !== null && amountTotal !== undefined ? Number(amountTotal) / 100 : null,
      currency: dataObj.currency ? String(dataObj.currency).toUpperCase() : null,
      status: String(dataObj.payment_status ?? "unknown"),
      raw: payload,
    };
  },

  async verifyTransaction(providerReference: string): Promise<VerificationResult> {
    const session = await stripeClient().checkout.sessions.retrieve(providerReference);
    const amountTotal = session.amount_total;
    const currency = session.currency;
    return {
      verified: session.payment_status === "paid",
      providerReference: session.id ?? providerReference,
      amount: amountTotal !== null && amountTotal !== undefined ? Number(amountTotal) / 100 : null,
      currency: typeof currency === "string" ? currency.toUpperCase() : null,
      txRef: session.client_reference_id ?? null,
    };
  },
};
