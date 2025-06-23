from repositories.payment_repo import *
from repositories.user_repo import checks_user_balance,update_user_balance,update_user_unlocked_chapters
from dotenv import load_dotenv
import os
load_dotenv()
FLUTTERWAVE_PUBLIC_KEY= os.getenv("FLUTTERWAVE_PUBLIC_KEY")
FLUTTERWAVE_SECRET_KEY=os.getenv("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_ENCRYPTION_KEY=os.getenv("FLUTTERWAVE_ENCRYPTION_KEY")
async def create_transaction(user_id: str, tx_type: TransactionType, number_of_stars: Optional[int] = None, amount: Optional[float] = None):
    transaction = TransactionIn(userId=user_id,TransactionType=tx_type,numberOfStars=number_of_stars,amount=amount)
    if tx_type==TransactionType.chapter_purchase:
        transactionOut =await create_transaction_history(transaction)
        await update_user_balance(userId= user_id,number_of_stars=number_of_stars)
        return transactionOut


async def pay_for_chapter(user_id: str,bundle_id:str,chapter_id: str) -> Optional[TransactionIn]:
    paymentBundle = await get_payment_bundle(bundle_id=bundle_id)
    balance = await checks_user_balance(userId=user_id)
    if balance >= paymentBundle.numberOfstars:
        transaction = await create_transaction(user_id=user_id,tx_type=TransactionType.chapter_purchase,number_of_stars=paymentBundle.numberOfstars)
        await update_user_unlocked_chapters(userId=user_id,chapterId=chapter_id)
        return transaction
    else:
        return None
    
    
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
