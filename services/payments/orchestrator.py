import time

from fastapi import HTTPException

from repositories.payment_repo import (
    create_payment_runtime,
    get_payment_bundle,
    get_payment_runtime_by_tx_ref,
    update_payment_runtime_status,
)
from schemas.payments_schema import (
    BundleType,
    CheckoutCreateRequest,
    CheckoutSessionOut,
    NormalizedWebhookEvent,
    PaymentProvider,
    PaymentRuntime,
    PaymentStatus,
)
from services.payments.fulfillment import fulfill_verified_payment
from services.payments.idempotency import mark_event_if_new
from services.payments.providers import FlutterwaveProvider, PaystackProvider, StripeProvider
from services.payments.routing import resolve_currency, resolve_provider


_provider_registry = {
    PaymentProvider.flutterwave: FlutterwaveProvider(),
    PaymentProvider.paystack: PaystackProvider(),
    PaymentProvider.stripe: StripeProvider(),
}


def _build_tx_ref(user_id: str, bundle_id: str) -> str:
    return f"uid:{user_id}|ts:{int(time.time())}|bid:{bundle_id}"


async def create_checkout(
    request: CheckoutCreateRequest,
    *,
    user_id: str,
    email: str,
    first_name: str | None,
    last_name: str | None,
) -> CheckoutSessionOut:
    bundle = await get_payment_bundle(bundle_id=request.bundleId)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Payment bundle not found")
    if bundle.bundleType == BundleType.subscription_stars:
        raise HTTPException(status_code=400, detail="Use wallet endpoint for stars subscription purchase")
    if bundle.amount is None or bundle.amount <= 0:
        raise HTTPException(status_code=400, detail="Checkout requires a cash-priced bundle")

    provider = resolve_provider(request.countryCode, request.provider)
    currency = resolve_currency(request.countryCode)
    tx_ref = _build_tx_ref(user_id=user_id, bundle_id=request.bundleId)

    adapter = _provider_registry[provider]
    session = await adapter.create_checkout_session(
        request,
        amount=float(bundle.amount),
        currency=currency,
        tx_ref=tx_ref,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    await create_payment_runtime(
        PaymentRuntime(
            txRef=tx_ref,
            userId=user_id,
            bundleId=request.bundleId,
            chapterId=request.chapterId,
            provider=provider,
            providerReference=session.providerReference,
            countryCode=request.countryCode.upper(),
            currency=currency,
            amount=float(bundle.amount),
            status=PaymentStatus.pending,
        )
    )

    return session


async def process_webhook(
    provider: PaymentProvider,
    *,
    raw_body: bytes,
    headers: dict[str, str],
) -> dict:
    adapter = _provider_registry[provider]
    event = await adapter.verify_webhook(raw_body=raw_body, headers=headers)

    is_new = await mark_event_if_new(
        provider=provider,
        event_id=event.eventId,
        tx_ref=event.txRef,
        provider_reference=event.providerReference,
    )
    if not is_new:
        return {"status": "idempotent_replay"}

    if not event.txRef:
        raise HTTPException(status_code=400, detail="Missing txRef in webhook event")

    runtime = await get_payment_runtime_by_tx_ref(tx_ref=event.txRef)
    if runtime is None:
        raise HTTPException(status_code=404, detail="Payment runtime not found")

    provider_ref = event.providerReference or runtime.providerReference
    if not provider_ref:
        raise HTTPException(status_code=400, detail="Missing provider reference")

    verification = await adapter.verify_transaction(provider_reference=provider_ref)
    if not verification.verified:
        await update_payment_runtime_status(tx_ref=runtime.txRef, status=PaymentStatus.failed)
        raise HTTPException(status_code=400, detail=verification.reason or "Verification failed")

    expected_amount = float(runtime.amount)
    if verification.amount is None or abs(float(verification.amount) - expected_amount) > 0.0001:
        await update_payment_runtime_status(tx_ref=runtime.txRef, status=PaymentStatus.failed)
        raise HTTPException(status_code=400, detail="Amount mismatch during verification")

    expected_currency = runtime.currency.upper()
    verified_currency = (verification.currency or "").upper()
    if not verified_currency or verified_currency != expected_currency:
        await update_payment_runtime_status(tx_ref=runtime.txRef, status=PaymentStatus.failed)
        raise HTTPException(status_code=400, detail="Currency mismatch during verification")

    await update_payment_runtime_status(
        tx_ref=runtime.txRef,
        status=PaymentStatus.verified,
        provider_reference=provider_ref,
    )

    fulfillment = await fulfill_verified_payment(
        user_id=runtime.userId,
        bundle_id=runtime.bundleId,
        tx_ref=runtime.txRef,
        chapter_id=runtime.chapterId,
    )

    await update_payment_runtime_status(
        tx_ref=runtime.txRef,
        status=PaymentStatus.fulfilled,
        provider_reference=provider_ref,
    )

    return {
        "status": "fulfilled",
        "txRef": runtime.txRef,
        "provider": provider.value,
        "fulfillment": fulfillment,
    }
