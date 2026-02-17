import json
import asyncio

import stripe
from fastapi import HTTPException

from schemas.payments_schema import (
    CheckoutCreateRequest,
    CheckoutSessionOut,
    NormalizedWebhookEvent,
    PaymentProvider,
    VerificationResult,
)
from services.payments.config import settings


class StripeProvider:
    async def create_checkout_session(
        self,
        request: CheckoutCreateRequest,
        *,
        amount: float,
        currency: str,
        tx_ref: str,
        email: str,
        first_name: str | None,
        last_name: str | None,
    ) -> CheckoutSessionOut:
        if not settings.stripe_enabled:
            raise HTTPException(status_code=503, detail="Stripe is disabled")

        stripe.api_key = settings.stripe_secret_key
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="payment",
            success_url=request.successUrl or "https://nattyboi-novelbackend.hf.space/success",
            cancel_url=request.cancelUrl or "https://nattyboi-novelbackend.hf.space/cancel",
            customer_email=email,
            client_reference_id=tx_ref,
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": int(amount * 100),
                        "product_data": {"name": "Mei payment"},
                    },
                }
            ],
            metadata={
                "bundleId": request.bundleId,
                "chapterId": request.chapterId or "",
                "countryCode": request.countryCode,
            },
        )

        return CheckoutSessionOut(
            checkoutUrl=session.url,
            provider=PaymentProvider.stripe,
            providerReference=session.id,
            txRef=tx_ref,
        )

    async def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> NormalizedWebhookEvent:
        signature = headers.get("stripe-signature")
        if not signature:
            raise HTTPException(status_code=403, detail="Missing stripe signature")

        stripe.api_key = settings.stripe_secret_key
        event = await asyncio.to_thread(
            stripe.Webhook.construct_event,
            payload=raw_body,
            sig_header=signature,
            secret=settings.stripe_webhook_secret,
        )
        payload = json.loads(raw_body.decode("utf-8"))
        data_obj = payload.get("data", {}).get("object", {})

        amount_total = data_obj.get("amount_total")
        return NormalizedWebhookEvent(
            provider=PaymentProvider.stripe,
            eventId=event["id"],
            txRef=data_obj.get("client_reference_id"),
            providerReference=data_obj.get("id"),
            amount=(float(amount_total) / 100.0) if amount_total is not None else None,
            currency=data_obj.get("currency", "").upper() if data_obj.get("currency") else None,
            status=str(data_obj.get("payment_status") or "unknown"),
            raw=payload,
        )

    async def verify_transaction(self, provider_reference: str) -> VerificationResult:
        stripe.api_key = settings.stripe_secret_key
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, provider_reference)
        amount_total = session.get("amount_total")
        currency = session.get("currency")
        tx_ref = session.get("client_reference_id")
        return VerificationResult(
            verified=session.get("payment_status") == "paid",
            providerReference=session.get("id", provider_reference),
            amount=(float(amount_total) / 100.0) if amount_total is not None else None,
            currency=currency.upper() if isinstance(currency, str) else None,
            txRef=tx_ref,
        )
