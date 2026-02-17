import hashlib
import hmac
import json

import httpx
from fastapi import HTTPException

from schemas.payments_schema import (
    CheckoutCreateRequest,
    CheckoutSessionOut,
    NormalizedWebhookEvent,
    PaymentProvider,
    VerificationResult,
)
from services.payments.config import settings


class PaystackProvider:
    base_url = "https://api.paystack.co"

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
        if not settings.paystack_enabled:
            raise HTTPException(status_code=503, detail="Paystack is disabled")

        payload = {
            "email": email,
            "amount": int(amount * 100),
            "currency": currency,
            "reference": tx_ref,
            "metadata": {
                "bundleId": request.bundleId,
                "chapterId": request.chapterId,
                "countryCode": request.countryCode,
                "firstName": first_name,
                "lastName": last_name,
            },
            "callback_url": request.successUrl,
        }
        headers = {
            "Authorization": f"Bearer {settings.paystack_secret_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/transaction/initialize", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json().get("data", {})

        return CheckoutSessionOut(
            checkoutUrl=data.get("authorization_url", ""),
            provider=PaymentProvider.paystack,
            providerReference=data.get("reference", tx_ref),
            txRef=tx_ref,
        )

    async def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> NormalizedWebhookEvent:
        signature = headers.get("x-paystack-signature")
        if not signature:
            raise HTTPException(status_code=403, detail="Missing paystack signature")

        computed = hmac.new(
            settings.paystack_webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(computed, signature):
            raise HTTPException(status_code=403, detail="Invalid paystack webhook signature")

        payload = json.loads(raw_body.decode("utf-8"))
        data = payload.get("data", {})
        amount = data.get("amount")
        return NormalizedWebhookEvent(
            provider=PaymentProvider.paystack,
            eventId=str(data.get("id") or payload.get("event") or "unknown"),
            txRef=data.get("reference"),
            providerReference=data.get("reference"),
            amount=(float(amount) / 100.0) if amount is not None else None,
            currency=data.get("currency"),
            status=str(data.get("status") or "unknown"),
            raw=payload,
        )

    async def verify_transaction(self, provider_reference: str) -> VerificationResult:
        headers = {"Authorization": f"Bearer {settings.paystack_secret_key}"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.get(f"{self.base_url}/transaction/verify/{provider_reference}", headers=headers)
            resp.raise_for_status()
            payload = resp.json().get("data", {})

        amount = payload.get("amount")
        return VerificationResult(
            verified=str(payload.get("status", "")).lower() == "success",
            providerReference=payload.get("reference", provider_reference),
            amount=(float(amount) / 100.0) if amount is not None else None,
            currency=payload.get("currency"),
            txRef=payload.get("reference"),
        )
