import asyncio

import pytest
from pydantic import ValidationError

from schemas.payments_schema import (
    BundleType,
    PaymentBundles,
    PaymentBundlesOut,
    PricingCatalogOut,
)
from services import payment_service


def test_payment_bundle_out_accepts_integer_date_created_and_normalizes_to_iso():
    bundle = PaymentBundlesOut.model_validate(
        {
            "_id": "a" * 24,
            "bundleType": BundleType.cash_to_star.value,
            "amount": 5000,
            "numberOfstars": 400,
            "description": "Starter stars",
            "dateCreated": 1731182400,
        }
    )

    assert bundle.id == "a" * 24
    assert isinstance(bundle.dateCreated, str)
    assert bundle.dateCreated.endswith("+00:00")


def test_payment_bundle_normalizes_legacy_subscription_type():
    bundle = PaymentBundles.model_validate(
        {
            "bundleType": BundleType.subscription.value,
            "amount": 2500,
            "durationDays": 30,
            "description": "Monthly cash plan",
        }
    )
    assert bundle.bundleType == BundleType.subscription_cash


def test_subscription_stars_bundle_requires_star_amount_and_duration():
    with pytest.raises(ValidationError):
        PaymentBundles.model_validate(
            {
                "bundleType": BundleType.subscription_stars.value,
                "description": "Broken stars plan",
            }
        )


def test_subscription_cash_bundle_rejects_star_amount():
    with pytest.raises(ValidationError):
        PaymentBundles.model_validate(
            {
                "bundleType": BundleType.subscription_cash.value,
                "amount": 3000,
                "numberOfstars": 50,
                "durationDays": 30,
                "description": "Invalid mixed plan",
            }
        )


def test_get_pricing_catalog_groups_bundles(monkeypatch):
    bundles = [
        PaymentBundlesOut.model_validate(
            {
                "_id": "1" * 24,
                "bundleType": BundleType.subscription_cash.value,
                "amount": 3000,
                "durationDays": 30,
                "description": "Monthly cash plan",
                "dateCreated": 1731182400,
            }
        ),
        PaymentBundlesOut.model_validate(
            {
                "_id": "2" * 24,
                "bundleType": BundleType.subscription_stars.value,
                "numberOfstars": 120,
                "durationDays": 30,
                "description": "Monthly stars plan",
                "dateCreated": 1731182400,
            }
        ),
        PaymentBundlesOut.model_validate(
            {
                "_id": "3" * 24,
                "bundleType": BundleType.cash_to_star.value,
                "amount": 2000,
                "numberOfstars": 80,
                "description": "Top-up",
                "dateCreated": 1731182400,
            }
        ),
        PaymentBundlesOut.model_validate(
            {
                "_id": "4" * 24,
                "bundleType": BundleType.star_to_book.value,
                "amount": 500,
                "numberOfstars": 20,
                "description": "Unlock chapter",
                "dateCreated": 1731182400,
            }
        ),
    ]

    async def fake_get_all_payment_bundles():
        return bundles

    monkeypatch.setattr(payment_service, "get_all_payment_bundles", fake_get_all_payment_bundles)
    catalog = asyncio.run(payment_service.get_pricing_catalog())

    assert isinstance(catalog, PricingCatalogOut)
    assert len(catalog.subscriptionPlans) == 2
    assert len(catalog.starBundles) == 1
    assert len(catalog.chapterUnlockBundles) == 1


def test_purchase_subscription_with_stars_success(monkeypatch):
    user_id = "9" * 24
    bundle_id = "8" * 24

    async def fake_get_payment_bundle(bundle_id: str):
        return PaymentBundlesOut.model_validate(
            {
                "_id": bundle_id,
                "bundleType": BundleType.subscription_stars.value,
                "numberOfstars": 100,
                "durationDays": 30,
                "description": "30-day stars plan",
                "dateCreated": 1731182400,
            }
        )

    async def fake_get_user_by_user_id(userId: str):
        return {"_id": user_id, "email": "reader@example.com"}

    async def fake_checks_user_balance(userId: str):
        return 200

    async def fake_create_transaction_history(transaction):
        return transaction

    async def fake_subtract_from_user_balance(userId: str, number_of_stars: int):
        return None

    async def fake_update_subscription(user_id: str, duration_days: int):
        return payment_service.UserOut.model_validate(
            {
                "_id": user_id,
                "email": "reader@example.com",
                "subscription": {
                    "active": True,
                    "expiresAt": "2026-12-31T00:00:00+00:00",
                },
            }
        )

    monkeypatch.setattr(payment_service, "get_payment_bundle", fake_get_payment_bundle)
    monkeypatch.setattr(payment_service, "get_user_by_userId", fake_get_user_by_user_id)
    monkeypatch.setattr(payment_service, "checks_user_balance", fake_checks_user_balance)
    monkeypatch.setattr(payment_service, "create_transaction_history", fake_create_transaction_history)
    monkeypatch.setattr(payment_service, "subtract_from_user_balance", fake_subtract_from_user_balance)
    monkeypatch.setattr(payment_service, "_update_subscription", fake_update_subscription)

    result = asyncio.run(
        payment_service.purchase_subscription_with_stars(user_id=user_id, bundle_id=bundle_id)
    )

    assert result.subscription is not None
    assert result.subscription.active is True
