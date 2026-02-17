from repositories.payment_repo import register_webhook_event
from schemas.payments_schema import PaymentProvider, WebhookEventRecord


async def mark_event_if_new(
    provider: PaymentProvider,
    event_id: str,
    tx_ref: str | None,
    provider_reference: str | None,
) -> bool:
    return await register_webhook_event(
        WebhookEventRecord(
            provider=provider,
            eventId=event_id,
            txRef=tx_ref,
            providerReference=provider_reference,
        )
    )
