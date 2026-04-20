import asyncio
import time
from datetime import datetime, timezone

from core.database import ASC, client, maybe_id
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

BUNDLE_COLLECTION = "payments"
TRANSACTION_COLLECTION = "transaction"
RUNTIME_COLLECTION = "payment_runtime"
WEBHOOK_EVENT_COLLECTION = "payment_webhook_events"


_runtime_indexes_ready = False
_runtime_indexes_lock = asyncio.Lock()


async def ensure_payment_runtime_indexes() -> None:
    """Create payment runtime indexes once per process.

    Previously this was awaited on every call to every runtime-repo function,
    which added a round-trip per query even though `create_index` is itself
    idempotent. A module-level flag + lock makes it a true one-shot.
    """
    global _runtime_indexes_ready
    if _runtime_indexes_ready:
        return
    async with _runtime_indexes_lock:
        if _runtime_indexes_ready:
            return
        await client.ensure_index(
            RUNTIME_COLLECTION,
            [("txRef", ASC)],
            unique=True,
            background=True,
        )
        await client.ensure_index(
            RUNTIME_COLLECTION,
            [("provider", ASC), ("providerReference", ASC)],
            background=True,
            sparse=True,
        )
        await client.ensure_index(
            WEBHOOK_EVENT_COLLECTION,
            [("provider", ASC), ("eventId", ASC)],
            unique=True,
            background=True,
        )
        _runtime_indexes_ready = True


# Bundle APIs
async def create_payment_bundle(bundle: PaymentBundles) -> PaymentBundlesOut:
    bundle_dict = bundle.model_dump(exclude_none=True)
    bundle_dict["dateCreated"] = int(time.time())
    created = await client.insert_and_fetch(BUNDLE_COLLECTION, bundle_dict)
    assert created is not None
    return PaymentBundlesOut(**created)


async def get_payment_bundle(bundle_id: str) -> PaymentBundlesOut | None:
    oid = maybe_id(bundle_id)
    if oid is None:
        return None
    bundle = await client.find_one(BUNDLE_COLLECTION, {"_id": oid})
    if bundle:
        return PaymentBundlesOut(**bundle)
    return None


async def get_all_payment_bundles(
    skip: int = 0, limit: int | None = None
) -> list[PaymentBundlesOut]:
    docs = await client.find_many(BUNDLE_COLLECTION, skip=skip, limit=limit)
    return [PaymentBundlesOut(**doc) for doc in docs]


async def count_all_payment_bundles() -> int:
    return await client.count(BUNDLE_COLLECTION)


async def update_payment_bundle(
    bundle_id: str, update_data: PaymentBundlesUpdate
) -> bool:
    oid = maybe_id(bundle_id)
    if oid is None:
        return False
    partial_update = update_data.model_dump(exclude_none=True)
    if not partial_update:
        return False
    partial_update["dateUpdated"] = int(time.time())
    modified = await client.update_one(
        BUNDLE_COLLECTION,
        {"_id": oid},
        {"set": partial_update},
    )
    return modified > 0


async def delete_payment_bundle(bundle_id: str) -> bool:
    oid = maybe_id(bundle_id)
    if oid is None:
        return False
    deleted = await client.delete_one(BUNDLE_COLLECTION, {"_id": oid})
    return deleted > 0


# Transaction history (legacy)
async def create_transaction_history(transaction: TransactionIn) -> TransactionOut:
    created = await client.insert_and_fetch(
        TRANSACTION_COLLECTION, transaction.model_dump()
    )
    assert created is not None
    return TransactionOut(**created)


async def get_transaction_history(transaction_id: str) -> TransactionOut | None:
    oid = maybe_id(transaction_id)
    if oid is None:
        return None
    transaction = await client.find_one(TRANSACTION_COLLECTION, {"_id": oid})
    if transaction:
        return TransactionOut(**transaction)
    return None


async def get_transaction_history_by_type(
    tx_type: TransactionType,
) -> list[TransactionOut]:
    docs = await client.find_many(
        TRANSACTION_COLLECTION, {"TransactionType": tx_type}
    )
    return [TransactionOut(**doc) for doc in docs]


async def get_all_transaction_history_for_user(userId: str) -> list[TransactionOut]:
    docs = await client.find_many(TRANSACTION_COLLECTION, {"userId": userId})
    return [TransactionOut(**doc) for doc in docs]


# Backward-compatible name.
async def get_all_transaction_history(userId: str) -> list[TransactionOut]:
    return await get_all_transaction_history_for_user(userId=userId)


async def get_transaction_history_by_paymentId(
    paymentId: str,
) -> TransactionOut | None:
    doc = await client.find_one(TRANSACTION_COLLECTION, {"paymentId": paymentId})
    if doc is None:
        return None
    return TransactionOut(**doc)


# Runtime payment records
async def create_payment_runtime(record: PaymentRuntime) -> PaymentRuntimeOut:
    await ensure_payment_runtime_indexes()
    created = await client.insert_and_fetch(
        RUNTIME_COLLECTION, record.model_dump()
    )
    assert created is not None
    return PaymentRuntimeOut(**created)


async def get_payment_runtime_by_tx_ref(tx_ref: str) -> PaymentRuntimeOut | None:
    await ensure_payment_runtime_indexes()
    doc = await client.find_one(RUNTIME_COLLECTION, {"txRef": tx_ref})
    if doc is None:
        return None
    return PaymentRuntimeOut(**doc)


async def update_payment_runtime_status(
    tx_ref: str,
    status: PaymentStatus,
    provider_reference: str | None = None,
) -> PaymentRuntimeOut | None:
    await ensure_payment_runtime_indexes()
    update_fields: dict[str, object] = {
        "status": status,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    if provider_reference:
        update_fields["providerReference"] = provider_reference

    updated: dict | None = await client.find_one_and_update(
        RUNTIME_COLLECTION,
        {"txRef": tx_ref},
        {"set": update_fields},
    )
    if updated is None:
        return None
    return PaymentRuntimeOut(**updated)


async def mark_payment_runtime_failed(tx_ref: str) -> PaymentRuntimeOut | None:
    return await update_payment_runtime_status(
        tx_ref=tx_ref, status=PaymentStatus.failed
    )


# Webhook idempotency
async def register_webhook_event(event: WebhookEventRecord) -> bool:
    await ensure_payment_runtime_indexes()
    try:
        await client.insert_one(WEBHOOK_EVENT_COLLECTION, event.model_dump())
        return True
    except Exception:
        return False


async def webhook_event_exists(
    provider: PaymentProvider, event_id: str
) -> bool:
    await ensure_payment_runtime_indexes()
    found = await client.find_one(
        WEBHOOK_EVENT_COLLECTION,
        {"provider": provider.value, "eventId": event_id},
    )
    return found is not None
