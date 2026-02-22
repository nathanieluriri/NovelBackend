from repositories.payment_repo import *
from schemas.user_schema import UserOut
from schemas.read_schema import MarkAsRead
from schemas.payments_schema import (
    BundleType,
    PricingBundleOut,
    PricingCatalogOut,
    SUBSCRIPTION_CASH_TYPES,
    SUBSCRIPTION_STAR_TYPES,
    TransactionType,
)
from repositories.read_repo import upsert_read_record
from repositories.user_repo import (
    get_user_by_userId,
    checks_user_balance,
    subtract_from_user_balance,
    add_to_user_balance,
    update_user_subscription,
)
from repositories.chapter_repo import get_chapter_by_chapter_id
from repositories.entitlement_repo import create_chapter_entitlement_if_absent
from services.access_service import is_chapter_unlocked
from schemas.chapter_schema import ChapterOut, ChapterAccessType
from dotenv import load_dotenv
from core.background_task import celery
from fastapi import HTTPException
from typing import Optional
import os
import asyncio
import time
from datetime import datetime, timezone, timedelta

load_dotenv()
FLUTTERWAVE_PUBLIC_KEY= os.getenv("FLUTTERWAVE_PUBLIC_KEY")
FLUTTERWAVE_SECRET_KEY=os.getenv("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_ENCRYPTION_KEY=os.getenv("FLUTTERWAVE_ENCRYPTION_KEY")



def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _is_subscription_active(subscription: Optional[dict]) -> bool:
    if not subscription:
        return False
    if not subscription.get("active"):
        return False
    expires_at = _parse_datetime(subscription.get("expiresAt"))
    if not expires_at:
        return False
    return expires_at > datetime.now(timezone.utc)


async def _unlock_chapter_for_user(user_id: str, chapter_id: str, tx_ref: Optional[str] = None):
    _, created = await create_chapter_entitlement_if_absent(
        userId=user_id,
        chapterId=chapter_id,
        source="stars_wallet",
        tx_ref=tx_ref,
    )
    if created:
        await upsert_read_record(data=MarkAsRead(userId=user_id,chapterId=chapter_id,hasRead=False))
    user = await get_user_by_userId(userId=user_id)
    return UserOut(**user), created


async def _update_subscription(user_id: str, duration_days: int) -> UserOut:
    user = await get_user_by_userId(userId=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_out = UserOut(**user)
    current = user_out.subscription.model_dump() if user_out.subscription else {}
    now = datetime.now(timezone.utc)
    current_expires_at = _parse_datetime(current.get("expiresAt"))
    base_time = current_expires_at if current_expires_at and current_expires_at > now else now
    new_expires_at = base_time + timedelta(days=duration_days)
    updated_subscription = {
        "active": True,
        "expiresAt": new_expires_at.isoformat(),
    }
    await update_user_subscription(userId=user_id, subscription=updated_subscription)
    refreshed_user = await get_user_by_userId(userId=user_id)
    return UserOut(**refreshed_user)


async def create_transaction(user_id: str, bundleId:str,tx_ref:Optional[str] = None,chapterId:Optional[str] = None,tx_type: TransactionType=TransactionType.chapter_purchase)->UserOut:
    epoch_time  = int(time.time())
    if tx_type==TransactionType.chapter_purchase:
        if chapterId is None:
            raise HTTPException(status_code=400, detail="chapterId is required for chapter purchase")
        payment = await get_payment_bundle(bundle_id=bundleId)
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment bundle not found")
        if payment.bundleType != BundleType.star_to_book:
            raise HTTPException(status_code=400, detail="Invalid bundle type for chapter purchase")
        if payment.numberOfstars is None:
            raise HTTPException(status_code=400, detail="Payment bundle missing stars")

        user = await get_user_by_userId(userId=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_out = UserOut(**user)
        already_unlocked = await is_chapter_unlocked(user=user_out, chapter_id=chapterId)
        if already_unlocked:
            return user_out

        balance = await checks_user_balance(userId=user_id)
        
        if balance >= payment.numberOfstars:
            chapter_tx_ref = tx_ref or f"uid:{user_id}||cid:{chapterId}||nos:{payment.numberOfstars}||ts:{epoch_time}"
            user_out, created = await _unlock_chapter_for_user(
                user_id=user_id,
                chapter_id=chapterId,
                tx_ref=chapter_tx_ref,
            )
            if created:
                transaction = TransactionIn(
                    userId=user_id,
                    paymentId=chapter_tx_ref,
                    TransactionType=tx_type,
                    numberOfStars=payment.numberOfstars,
                    amount=payment.amount,
                )
                await create_transaction_history(transaction)
                await subtract_from_user_balance(userId= user_id,number_of_stars=payment.numberOfstars)
            return user_out
        else:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
    elif tx_type==TransactionType.real_cash:
        
        payment = await get_payment_bundle(bundle_id=bundleId)
        if payment:
            if payment.amount is None or payment.amount <= 0:
                raise HTTPException(status_code=400, detail="Cash bundle is missing amount")
            indempotent_check = await get_transaction_history_by_paymentId(paymentId=tx_ref)
            if indempotent_check==None:
                if payment.numberOfstars is None:
                    raise HTTPException(status_code=400, detail="Payment bundle missing stars")
                transaction = TransactionIn(userId=user_id,paymentId=tx_ref, TransactionType=tx_type,numberOfStars=payment.numberOfstars,amount=payment.amount)
                await create_transaction_history(transaction)
                await add_to_user_balance(userId= user_id,number_of_stars=payment.numberOfstars)
                User = await get_user_by_userId(userId=user_id)
                userOut = UserOut(**User)
                return userOut
            User = await get_user_by_userId(userId=user_id)
            userOut = UserOut(**User)
            return userOut
    elif tx_type == TransactionType.subscription_purchase:
        payment = await get_payment_bundle(bundle_id=bundleId)
        if (
            not payment
            or payment.durationDays is None
            or payment.bundleType not in SUBSCRIPTION_CASH_TYPES
            or payment.amount is None
            or payment.amount <= 0
        ):
            raise HTTPException(status_code=400, detail="Subscription bundle is invalid")
        indempotent_check = await get_transaction_history_by_paymentId(paymentId=tx_ref)
        if indempotent_check is None:
            transaction = TransactionIn(
                userId=user_id,
                paymentId=tx_ref,
                TransactionType=tx_type,
                numberOfStars=0,
                amount=payment.amount,
            )
            await create_transaction_history(transaction)
            return await _update_subscription(user_id=user_id, duration_days=payment.durationDays)
        user = await get_user_by_userId(userId=user_id)
        return UserOut(**user)

    raise HTTPException(status_code=400, detail="Unsupported transaction type")


async def pay_for_chapter(user_id: str,bundle_id:str,chapter_id: str) -> Optional[UserOut]:
    user = await get_user_by_userId(userId=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chapter = await get_chapter_by_chapter_id(chapterId=chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    chapter_out = ChapterOut(**chapter)
    await chapter_out.model_async_validate()
    if chapter_out.accessType != ChapterAccessType.paid:
        raise HTTPException(status_code=409, detail="Chapter does not require paid unlock")

    if chapter_out.unlockBundleId and chapter_out.unlockBundleId != bundle_id:
        raise HTTPException(status_code=400, detail="Invalid bundle for chapter unlock")

    return await create_transaction(
        bundleId=bundle_id,
        user_id=user_id,
        chapterId=chapter_id,
        tx_type=TransactionType.chapter_purchase,
    )
    
    

def createLink(userId,email,amount,bundle_id,bundle_description,firstName=None,lastName=None,):
    import time
    import requests
    
    firstName = firstName if firstName is not None else "Stranger"
    lastName = lastName if lastName is not None else "Stranger"
    
    epoch_time = int(time.time())
    
    url = 'https://api.flutterwave.com/v3/payments'

    payload = {
        "tx_ref": f"uid:{userId}|ts:{epoch_time}|bid:{bundle_id}",
        "amount": f"{amount}",
        "currency": "NGN",
        "redirect_url": "https://nattyboi-novelbackend.hf.space/success",
        "customer": {
            "email":email,
            "name": f"{firstName} {lastName}"
        },
        "customizations": {
            "title": "Star Purchase With Mei ",
            "logo": "https://iili.io/3DKqndN.jpg",
            "description":bundle_description
        },
        "configurations": {
				"session_duration": 10,
				"max_retry_attempt": 5, 
			},
        "meta":{
            "userId":userId,
            "bundleId":bundle_id,
            "time":epoch_time
        }
    }

    headers = {
        "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",  # Replace with your real secret key
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
        return response.json()['data']
    except requests.exceptions.RequestException as err:
        print("Request error:", err)
        if err.response is not None:
            print("Error response:", err.response.text)


async def record_purchase_of_stars(userId: str, tx_ref,bundleId: str,):
    
    return await create_transaction(bundleId=bundleId,user_id=userId,tx_ref=tx_ref, tx_type=TransactionType.real_cash,)


async def record_subscription_purchase(userId: str, tx_ref: str, bundleId: str) -> UserOut:
    return await create_transaction(
        bundleId=bundleId,
        user_id=userId,
        tx_ref=tx_ref,
        tx_type=TransactionType.subscription_purchase,
    )


async def purchase_subscription_with_stars(user_id: str, bundle_id: str) -> UserOut:
    payment = await get_payment_bundle(bundle_id=bundle_id)
    if (
        payment is None
        or payment.bundleType not in SUBSCRIPTION_STAR_TYPES
        or payment.numberOfstars is None
        or payment.numberOfstars <= 0
        or payment.durationDays is None
        or payment.durationDays <= 0
    ):
        raise HTTPException(status_code=400, detail="Subscription stars bundle is invalid")

    user = await get_user_by_userId(userId=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    balance = await checks_user_balance(userId=user_id)
    if balance is None or balance < payment.numberOfstars:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    tx_ref = f"uid:{user_id}||bid:{bundle_id}||nos:{payment.numberOfstars}||ts:{int(time.time())}"
    transaction = TransactionIn(
        userId=user_id,
        paymentId=tx_ref,
        TransactionType=TransactionType.subscription_purchase,
        numberOfStars=payment.numberOfstars,
        amount=payment.amount or 0,
    )
    await create_transaction_history(transaction)
    await subtract_from_user_balance(userId=user_id, number_of_stars=payment.numberOfstars)
    return await _update_subscription(user_id=user_id, duration_days=payment.durationDays)


def _as_pricing_bundle(bundle) -> PricingBundleOut:
    return PricingBundleOut(
        id=bundle.id,
        bundleType=bundle.bundleType,
        description=bundle.description,
        durationDays=bundle.durationDays,
        cashAmount=bundle.amount,
        starAmount=bundle.numberOfstars,
        dateCreated=bundle.dateCreated,
    )


async def get_pricing_catalog() -> PricingCatalogOut:
    bundles = await get_all_payment_bundles()
    subscriptions = []
    star_bundles = []
    chapter_unlock_bundles = []

    for bundle in bundles:
        if bundle.bundleType is None:
            continue
        item = _as_pricing_bundle(bundle)
        if bundle.bundleType in SUBSCRIPTION_CASH_TYPES or bundle.bundleType in SUBSCRIPTION_STAR_TYPES:
            subscriptions.append(item)
            continue
        if bundle.bundleType in {BundleType.cash_to_star, BundleType.cash_promo}:
            star_bundles.append(item)
            continue
        if bundle.bundleType == BundleType.star_to_book:
            chapter_unlock_bundles.append(item)

    return PricingCatalogOut(
        subscriptionPlans=subscriptions,
        starBundles=star_bundles,
        chapterUnlockBundles=chapter_unlock_bundles,
    )
