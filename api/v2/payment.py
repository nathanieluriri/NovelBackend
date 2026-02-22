from fastapi import APIRouter, Depends, HTTPException

from repositories.payment_repo import count_all_payment_bundles, get_all_payment_bundles
from schemas.listing_schema import PaginatedListOut
from schemas.payments_schema import PaymentBundlesOut
from security.auth import verify_any_token
from services.listing_service import build_list_payload, clamp_limit

router = APIRouter()


@router.get("/get-payment-bundles", response_model=PaginatedListOut[PaymentBundlesOut], dependencies=[Depends(verify_any_token)])
async def get_payment_bundles_v2(skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await get_all_payment_bundles(skip=skip, limit=safe_limit)
    total = await count_all_payment_bundles()
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)
