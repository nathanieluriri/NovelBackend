/**
 * Provider routing by countryCode — port of `services/payments/routing.py`
 * (payments.md §1).
 * - NG → provider required, must be flutterwave or paystack (else 400).
 * - Any other country → forced stripe; explicit flutterwave/paystack → 400.
 * - Currency: NGN for NG, USD otherwise (no FX table).
 */
import { HttpError } from "@/lib/http/errors";
import type { PaymentProvider } from "./contracts";

export function resolveProvider(
  countryCode: string,
  requestedProvider?: PaymentProvider | null,
): PaymentProvider {
  const normalized = countryCode.toUpperCase();

  if (normalized === "NG") {
    if (requestedProvider === null || requestedProvider === undefined) {
      throw new HttpError(400, "provider is required for NG checkouts");
    }
    if (requestedProvider !== "flutterwave" && requestedProvider !== "paystack") {
      throw new HttpError(400, "NG supports only flutterwave or paystack");
    }
    return requestedProvider;
  }

  if (requestedProvider === "flutterwave" || requestedProvider === "paystack") {
    throw new HttpError(400, "Non-NG checkouts support only stripe");
  }

  return "stripe";
}

export function resolveCurrency(countryCode: string): string {
  return countryCode.toUpperCase() === "NG" ? "NGN" : "USD";
}
