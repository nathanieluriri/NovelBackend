from typing import Protocol

from schemas.payments_schema import (
    CheckoutCreateRequest,
    CheckoutSessionOut,
    NormalizedWebhookEvent,
    VerificationResult,
)


class PaymentProviderAdapter(Protocol):
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
        ...

    async def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> NormalizedWebhookEvent:
        ...

    async def verify_transaction(self, provider_reference: str) -> VerificationResult:
        ...
