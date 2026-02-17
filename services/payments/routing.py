from fastapi import HTTPException

from schemas.payments_schema import PaymentProvider


def resolve_provider(country_code: str, requested_provider: PaymentProvider | None) -> PaymentProvider:
    normalized = country_code.upper()

    if normalized == "NG":
        if requested_provider is None:
            raise HTTPException(status_code=400, detail="provider is required for NG checkouts")
        if requested_provider not in (PaymentProvider.flutterwave, PaymentProvider.paystack):
            raise HTTPException(status_code=400, detail="NG supports only flutterwave or paystack")
        return requested_provider

    if requested_provider in (PaymentProvider.flutterwave, PaymentProvider.paystack):
        raise HTTPException(status_code=400, detail="Non-NG checkouts support only stripe")

    return PaymentProvider.stripe


def resolve_currency(country_code: str) -> str:
    return "NGN" if country_code.upper() == "NG" else "USD"
