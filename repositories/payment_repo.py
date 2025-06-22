from bson import ObjectId
from core.database import db
from schemas.payments_schema import *

bundle_collection =db.payments
transaction_collection=db.transaction
# CREATE
async def create_payment_bundle(bundle: PaymentBundles)->PaymentBundlesOut:
    bundle_dict=bundle.model_dump()
    result = await bundle_collection.insert_one(bundle_dict)
    paymentObj =await bundle_collection.find_one({"_id":ObjectId(result.inserted_id)})
    paymentOut = PaymentBundlesOut(**paymentObj)
    return paymentOut

# READ (get one by ID)
async def get_payment_bundle(bundle_id: str)->PaymentBundlesOut:
    bundle = await bundle_collection.find_one({"_id": ObjectId(bundle_id)})
    if bundle:
        return PaymentBundlesOut(**bundle)
    return None

# READ ALL
async def get_all_payment_bundles()->List[PaymentBundlesOut]:
    bundles = []
    async for doc in bundle_collection.find():
        bundles.append(PaymentBundlesOut(**doc))
    return bundles

# UPDATE
async def update_payment_bundle(bundle_id: str, update_data: PaymentBundlesUpdate)->bool:
    update_data = update_data.model_dump(exclude=None)
    result = await bundle_collection.update_one(
        {"_id": ObjectId(bundle_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

# DELETE
async def delete_payment_bundle(bundle_id: str)->bool:
    result = await bundle_collection.delete_one({"_id": ObjectId(bundle_id)})
    return result.deleted_count > 0










# CREATE
async def create_transaction_history(transaction: TransactionIn)->TransactionOut:
    transaction_dict=transaction.model_dump()
    transaction_result = await transaction_collection.insert_one(transaction_dict)
    transaction_Obj =await transaction_collection.find_one({"_id":ObjectId(transaction_result.inserted_id)})
    transactionOut = TransactionOut(**transaction_Obj)
    return transactionOut

# READ (get one by ID)
async def get_transaction_history(transaction_id: str)->PaymentBundlesOut:
    transaction = await transaction_collection.find_one({"_id": ObjectId(transaction_id)})
    if transaction:
        return TransactionOut(**transaction)
    return None

# READ ALL
async def get_all_transaction_history()->List[PaymentBundlesOut]:
    bundles = []
    async for doc in transaction_collection.find():
        bundles.append(TransactionOut(**doc))
    return bundles

# READ ALL BY TransactionType
async def get_transaction_history_by_type(tx_type: TransactionType) -> List[TransactionOut]:
    transactions = []
    async for doc in transaction_collection.find({"TransactionType": tx_type}):
        transactions.append(TransactionOut(**doc))
    return transactions



# READ ALL FOR ONE USER
async def get_all_transaction_history(userId:str)->List[PaymentBundlesOut]:
    bundles = []
    async for doc in transaction_collection.find({"userId":userId}):
        bundles.append(TransactionOut(**doc))
    return bundles


# DELETE
async def delete_payment_bundle(bundle_id: str)->bool:
    result = await bundle_collection.delete_one({"_id": ObjectId(bundle_id)})
    return result.deleted_count > 0
