import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentSettings:
    flutterwave_secret_key: str
    flutterwave_webhook_secret: str
    paystack_secret_key: str
    paystack_webhook_secret: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    orchestrator_enabled: bool
    paystack_enabled: bool
    stripe_enabled: bool
    entitlements_write_enabled: bool
    provider_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "PaymentSettings":
        return cls(
            flutterwave_secret_key=os.getenv("FLUTTERWAVE_SECRET_KEY", ""),
            flutterwave_webhook_secret=os.getenv("FLW_WEBHOOK_SECRET_HASH", ""),
            paystack_secret_key=os.getenv("PAYSTACK_SECRET_KEY", ""),
            paystack_webhook_secret=os.getenv("PAYSTACK_WEBHOOK_SECRET", ""),
            stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", ""),
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
            orchestrator_enabled=os.getenv("PAYMENTS_ORCHESTRATOR_ENABLED", "true").lower() == "true",
            paystack_enabled=os.getenv("PAYSTACK_ENABLED", "true").lower() == "true",
            stripe_enabled=os.getenv("STRIPE_ENABLED", "true").lower() == "true",
            entitlements_write_enabled=os.getenv("ENTITLEMENTS_WRITE_ENABLED", "true").lower() == "true",
            provider_timeout_seconds=float(os.getenv("PAYMENTS_PROVIDER_TIMEOUT_SECONDS", "10")),
        )


settings = PaymentSettings.from_env()
