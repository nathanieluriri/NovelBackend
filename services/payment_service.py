from repositories.payment_repo import *
from schemas.user_schema import UserOut
from repositories.user_repo import get_user_by_userId,checks_user_balance,subtract_from_user_balance,update_user_unlocked_chapters,add_to_user_balance
from dotenv import load_dotenv
from core.background_task import celery
from fastapi import HTTPException
import os
import asyncio
import time

load_dotenv()
FLUTTERWAVE_PUBLIC_KEY= os.getenv("FLUTTERWAVE_PUBLIC_KEY")
FLUTTERWAVE_SECRET_KEY=os.getenv("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_ENCRYPTION_KEY=os.getenv("FLUTTERWAVE_ENCRYPTION_KEY")




async def create_transaction(user_id: str, bundleId:str,tx_ref:Optional[str] = None,chapterId:Optional[str] = None,tx_type: TransactionType=TransactionType.chapter_purchase)->UserOut:
    epoch_time  = int(time.time())
    if tx_type==TransactionType.chapter_purchase:
        payment = await get_payment_bundle(bundle_id=bundleId)
        balance = await checks_user_balance(userId=user_id)
        
        if balance >= payment.numberOfstars:
            await update_user_unlocked_chapters(userId=user_id,chapterId=chapterId)
            transaction = TransactionIn(userId=user_id,paymentId=f"uid:{user_id}||nos:{payment.numberOfstars}||ts:{epoch_time}", TransactionType=tx_type,numberOfStars=payment.numberOfstars,amount=payment.amount)
            transactionOut =await create_transaction_history(transaction)
            await subtract_from_user_balance(userId= user_id,number_of_stars=payment.numberOfstars)
            User = await get_user_by_userId(userId=user_id)
            userOut = UserOut(**User)
            return userOut
        else:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
    elif tx_type==TransactionType.real_cash:
        
        payment = await get_payment_bundle(bundle_id=bundleId)
        if payment:
            transaction = TransactionIn(userId=user_id,paymentId=tx_ref, TransactionType=tx_type,numberOfStars=payment.numberOfstars,amount=payment.amount)
            transactionOut =await create_transaction_history(transaction)
            await add_to_user_balance(userId= user_id,number_of_stars=payment.numberOfstars)
            User = await get_user_by_userId(userId=user_id)
            userOut = UserOut(**User)
            return userOut



async def pay_for_chapter(user_id: str,bundle_id:str,chapter_id: str) -> Optional[TransactionIn]:
    transaction = await create_transaction(user_id=user_id,tx_type=TransactionType.chapter_purchase,bundleId=bundle_id,chapterId=chapter_id)
    return transaction
    
    

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

