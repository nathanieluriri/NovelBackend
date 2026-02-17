from fastapi import HTTPException

from repositories.entitlement_repo import create_chapter_entitlement_if_absent
from repositories.payment_repo import get_payment_bundle
from repositories.read_repo import upsert_read_record
from schemas.payments_schema import BundleType, EntitlementGrantType
from schemas.read_schema import MarkAsRead
from services.payment_service import record_purchase_of_stars, record_subscription_purchase


async def fulfill_verified_payment(
    *,
    user_id: str,
    bundle_id: str,
    tx_ref: str,
    chapter_id: str | None,
) -> dict:
    bundle = await get_payment_bundle(bundle_id=bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Payment bundle not found")

    if bundle.bundleType == BundleType.subscription:
        user_out = await record_subscription_purchase(userId=user_id, tx_ref=tx_ref, bundleId=bundle_id)
        return {
            "grantType": EntitlementGrantType.subscription,
            "userId": user_out.userId,
        }

    if bundle.bundleType == BundleType.star_to_book:
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapterId is required for chapter unlock")
        _, created = await create_chapter_entitlement_if_absent(
            userId=user_id,
            chapterId=chapter_id,
            source="cash_checkout",
            tx_ref=tx_ref,
        )
        if created:
            await upsert_read_record(data=MarkAsRead(userId=user_id, chapterId=chapter_id, hasRead=False))
        return {
            "grantType": EntitlementGrantType.chapter_unlock,
            "chapterId": chapter_id,
            "created": created,
        }

    user_out = await record_purchase_of_stars(userId=user_id, tx_ref=tx_ref, bundleId=bundle_id)
    return {
        "grantType": EntitlementGrantType.wallet_credit,
        "userId": user_out.userId,
    }
