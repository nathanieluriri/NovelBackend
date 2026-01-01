from repositories.payment_repo import *
from schemas.user_schema import UserOut
from schemas.read_schema import MarkAsRead
from repositories.read_repo import upsert_read_record
from repositories.user_repo import (
    get_user_by_userId,
    checks_user_balance,
    subtract_from_user_balance,
    update_user_unlocked_chapters,
    add_to_user_balance,
    update_user_subscription,
)
from dotenv import load_dotenv
from core.background_task import celery
from fastapi import HTTPException
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


async def _unlock_chapter_for_user(user_id: str, chapter_id: str) -> UserOut:
    unlock_succes = await update_user_unlocked_chapters(userId=user_id,chapterId=chapter_id)
    if not unlock_succes:
        raise HTTPException(status_code=500,detail="Most likely done before or user doesnt exist")

    await upsert_read_record(data=MarkAsRead(userId=user_id,chapterId=chapter_id,hasRead=False))
    user = await get_user_by_userId(userId=user_id)
    return UserOut(**user)


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
        payment = await get_payment_bundle(bundle_id=bundleId)
        balance = await checks_user_balance(userId=user_id)
        
        if balance >= payment.numberOfstars:
            user_out = await _unlock_chapter_for_user(user_id=user_id,chapter_id=chapterId)
            transaction = TransactionIn(userId=user_id,paymentId=f"uid:{user_id}||nos:{payment.numberOfstars}||ts:{epoch_time}", TransactionType=tx_type,numberOfStars=payment.numberOfstars,amount=payment.amount)
            await create_transaction_history(transaction)
            await subtract_from_user_balance(userId= user_id,number_of_stars=payment.numberOfstars)
            return user_out
        else:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
    elif tx_type==TransactionType.real_cash:
        
        payment = await get_payment_bundle(bundle_id=bundleId)
        if payment:
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
        if not payment or payment.durationDays is None:
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


async def pay_for_chapter(user_id: str,bundle_id:str,chapter_id: str) -> Optional[UserOut]:
    user = await get_user_by_userId(userId=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_out = UserOut(**user)
    if not _is_subscription_active(user_out.subscription.model_dump() if user_out.subscription else None):
        raise HTTPException(status_code=402, detail="Active subscription required")
    return await _unlock_chapter_for_user(user_id=user_id,chapter_id=chapter_id)
    
    

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
