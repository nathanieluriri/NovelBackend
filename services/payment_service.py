from repositories.payment_repo import *
from repositories.user_repo import checks_user_balance,update_user_balance,update_user_unlocked_chapters


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