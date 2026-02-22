import time
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ASCENDING

from core.database import db
from schemas.payments_schema import (
    PaymentBundles,
    PaymentBundlesOut,
    PaymentBundlesUpdate,
    PaymentProvider,
    PaymentRuntime,
    PaymentRuntimeOut,
    PaymentStatus,
    TransactionIn,
    TransactionOut,
    TransactionType,
    WebhookEventRecord,
)


bundle_collection = db.payments
transaction_collection = db.transaction
runtime_collection = db.payment_runtime
webhook_event_collection = db.payment_webhook_events


async def ensure_payment_runtime_indexes():
    await runtime_collection.create_index([("txRef", ASCENDING)], unique=True, background=True)
    await runtime_collection.create_index(
        [("provider", ASCENDING), ("providerReference", ASCENDING)],
        background=True,
        sparse=True,
    )
    await webhook_event_collection.create_index(
        [("provider", ASCENDING), ("eventId", ASCENDING)],
        unique=True,
        background=True,
    )


# Bundle APIs
async def create_payment_bundle(bundle: PaymentBundles) -> PaymentBundlesOut:
    bundle_dict = bundle.model_dump(exclude_none=True)
    bundle_dict["dateCreated"] = int(time.time())
    result = await bundle_collection.insert_one(bundle_dict)
    payment_obj = await bundle_collection.find_one({"_id": ObjectId(result.inserted_id)})
    return PaymentBundlesOut(**payment_obj)


async def get_payment_bundle(bundle_id: str) -> PaymentBundlesOut | None:
    bundle = await bundle_collection.find_one({"_id": ObjectId(bundle_id)})
    if bundle:
        return PaymentBundlesOut(**bundle)
    return None


async def get_all_payment_bundles() -> list[PaymentBundlesOut]:
    bundles = []
    async for doc in bundle_collection.find():
        bundles.append(PaymentBundlesOut(**doc))
    return bundles


async def update_payment_bundle(bundle_id: str, update_data: PaymentBundlesUpdate) -> bool:
    current = await bundle_collection.find_one({"_id": ObjectId(bundle_id)})
    if current is None:
        return False

    partial_update = update_data.model_dump(exclude_none=True)
    merged = {
        "bundleType": partial_update.get("bundleType", current.get("bundleType")),
        "amount": partial_update.get("amount", current.get("amount")),
        "numberOfstars": partial_update.get("numberOfstars", current.get("numberOfstars")),
        "durationDays": partial_update.get("durationDays", current.get("durationDays")),
        "description": partial_update.get("description", current.get("description")),
    }
    validated = PaymentBundles.model_validate(merged)
    update_payload = validated.model_dump(exclude_none=True)
    update_payload["dateUpdated"] = int(time.time())

    result = await bundle_collection.update_one(
        {"_id": ObjectId(bundle_id)},
        {"$set": update_payload},
    )
    return result.modified_count > 0


async def delete_payment_bundle(bundle_id: str) -> bool:
    result = await bundle_collection.delete_one({"_id": ObjectId(bundle_id)})
    return result.deleted_count > 0


# Transaction history (legacy)
async def create_transaction_history(transaction: TransactionIn) -> TransactionOut:
    transaction_dict = transaction.model_dump()
    transaction_result = await transaction_collection.insert_one(transaction_dict)
    transaction_obj = await transaction_collection.find_one({"_id": ObjectId(transaction_result.inserted_id)})
    return TransactionOut(**transaction_obj)


async def get_transaction_history(transaction_id: str) -> TransactionOut | None:
    transaction = await transaction_collection.find_one({"_id": ObjectId(transaction_id)})
    if transaction:
        return TransactionOut(**transaction)
    return None


async def get_transaction_history_by_type(tx_type: TransactionType) -> list[TransactionOut]:
    transactions = []
    async for doc in transaction_collection.find({"TransactionType": tx_type}):
        transactions.append(TransactionOut(**doc))
    return transactions


async def get_all_transaction_history_for_user(userId: str) -> list[TransactionOut]:
    txns = []
    async for doc in transaction_collection.find({"userId": userId}):
        txns.append(TransactionOut(**doc))
    return txns


# Backward-compatible name.
async def get_all_transaction_history(userId: str) -> list[TransactionOut]:
    return await get_all_transaction_history_for_user(userId=userId)


async def get_transaction_history_by_paymentId(paymentId: str) -> TransactionOut | None:
    doc = await transaction_collection.find_one({"paymentId": paymentId})
    if doc is None:
        return None
    return TransactionOut(**doc)


# Runtime payment records
async def create_payment_runtime(record: PaymentRuntime) -> PaymentRuntimeOut:
    await ensure_payment_runtime_indexes()
    payload = record.model_dump()
    result = await runtime_collection.insert_one(payload)
    created = await runtime_collection.find_one({"_id": result.inserted_id})
    return PaymentRuntimeOut(**created)


async def get_payment_runtime_by_tx_ref(tx_ref: str) -> PaymentRuntimeOut | None:
    await ensure_payment_runtime_indexes()
    doc = await runtime_collection.find_one({"txRef": tx_ref})
    if doc is None:
        return None
    return PaymentRuntimeOut(**doc)


async def update_payment_runtime_status(
    tx_ref: str,
    status: PaymentStatus,
    provider_reference: str | None = None,
) -> PaymentRuntimeOut | None:
    await ensure_payment_runtime_indexes()
    update_payload: dict[str, object] = {
        "status": status,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    if provider_reference:
        update_payload["providerReference"] = provider_reference

    await runtime_collection.update_one({"txRef": tx_ref}, {"$set": update_payload})
    updated = await runtime_collection.find_one({"txRef": tx_ref})
    if updated is None:
        return None
    return PaymentRuntimeOut(**updated)


async def mark_payment_runtime_failed(tx_ref: str) -> PaymentRuntimeOut | None:
    return await update_payment_runtime_status(tx_ref=tx_ref, status=PaymentStatus.failed)


# Webhook idempotency
async def register_webhook_event(event: WebhookEventRecord) -> bool:
    await ensure_payment_runtime_indexes()
    payload = event.model_dump()
    try:
        await webhook_event_collection.insert_one(payload)
        return True
    except Exception:
        return False


async def webhook_event_exists(provider: PaymentProvider, event_id: str) -> bool:
    await ensure_payment_runtime_indexes()
    found = await webhook_event_collection.find_one({"provider": provider.value, "eventId": event_id})
    return found is not None
