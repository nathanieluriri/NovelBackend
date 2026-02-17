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


class FlutterwaveProvider:
    base_url = "https://api.flutterwave.com/v3"

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
        payload = {
            "tx_ref": tx_ref,
            "amount": f"{amount}",
            "currency": currency,
            "redirect_url": request.successUrl or "https://nattyboi-novelbackend.hf.space/success",
            "customer": {
                "email": email,
                "name": f"{first_name or 'Stranger'} {last_name or 'Stranger'}",
            },
            "meta": {
                "bundleId": request.bundleId,
                "chapterId": request.chapterId,
                "countryCode": request.countryCode,
            },
        }
        headers = {
            "Authorization": f"Bearer {settings.flutterwave_secret_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/payments", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json().get("data", {})

        return CheckoutSessionOut(
            checkoutUrl=data.get("link", ""),
            provider=PaymentProvider.flutterwave,
            providerReference=str(data.get("id") or ""),
            txRef=tx_ref,
        )

    async def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> NormalizedWebhookEvent:
        header_hash = headers.get("verif-hash") or headers.get("verif_hash")
        if not header_hash or header_hash != settings.flutterwave_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid flutterwave webhook signature")

        import json

        payload = json.loads(raw_body.decode("utf-8"))
        data = payload.get("data", {})
        return NormalizedWebhookEvent(
            provider=PaymentProvider.flutterwave,
            eventId=str(data.get("id") or payload.get("event") or "unknown"),
            txRef=data.get("tx_ref"),
            providerReference=str(data.get("id") or data.get("flw_ref") or ""),
            amount=float(data.get("amount")) if data.get("amount") is not None else None,
            currency=data.get("currency"),
            status=str(data.get("status") or "unknown"),
            raw=payload,
        )

    async def verify_transaction(self, provider_reference: str) -> VerificationResult:
        headers = {"Authorization": f"Bearer {settings.flutterwave_secret_key}"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.get(f"{self.base_url}/transactions/{provider_reference}/verify", headers=headers)
            resp.raise_for_status()
            payload = resp.json().get("data", {})

        return VerificationResult(
            verified=str(payload.get("status", "")).lower() == "successful",
            providerReference=str(payload.get("id") or provider_reference),
            amount=float(payload.get("amount")) if payload.get("amount") is not None else None,
            currency=payload.get("currency"),
            txRef=payload.get("tx_ref"),
        )
