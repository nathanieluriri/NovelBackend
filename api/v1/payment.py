from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from repositories.payment_repo import (
    create_payment_bundle,
    delete_payment_bundle,
    get_all_payment_bundles,
    get_payment_bundle,
    update_payment_bundle,
)
from schemas.payments_schema import (
    ChapterPayment,
    CheckoutCreateRequest,
    PaymentBundles,
    PaymentBundlesOut,
    PaymentBundlesUpdate,
    PaymentLink,
    PaymentProvider,
)
from security.auth import verify_admin_token, verify_any_token, verify_token
from services.payments import create_checkout, process_webhook
from services.payment_service import pay_for_chapter
from services.user_service import get_user_details_with_accessToken

router = APIRouter()


@router.post("/create-payment-bundle", dependencies=[Depends(verify_admin_token)])
async def create_payment_bundle_route(paymentBundle: PaymentBundles) -> PaymentBundlesOut:
    return await create_payment_bundle(bundle=paymentBundle)


@router.get("/get-payment-bundles", dependencies=[Depends(verify_any_token)])
async def get_payment_bundle_route() -> list[PaymentBundlesOut]:
    return await get_all_payment_bundles()


@router.patch("/update-payment-bundle/{bundleId}", dependencies=[Depends(verify_admin_token)])
async def update_payment_bundle_route(bundleId: str, paymentBundle: PaymentBundlesUpdate):
    if len(bundleId) != 24:
        raise HTTPException(status_code=400, detail="bundleId must be exactly 24 characters long")
    updated = await update_payment_bundle(bundle_id=bundleId, update_data=paymentBundle)
    return JSONResponse(content={"message": updated})


@router.delete("/delete-payment-bundle/{bundleId}", dependencies=[Depends(verify_admin_token)])
async def delete_payment_bundle_route(bundleId: str):
    if len(bundleId) != 24:
        raise HTTPException(status_code=400, detail="bundleId must be exactly 24 characters long")
    deleted = await delete_payment_bundle(bundle_id=bundleId)
    return JSONResponse(content={"message": deleted})


@router.post("/checkout/create")
async def create_checkout_route(request_data: CheckoutCreateRequest, dep=Depends(verify_token)):
    user = await get_user_details_with_accessToken(token=dep["accessToken"])
    if not user:
        raise HTTPException(status_code=401, detail="User details not found or unauthorized")

    session = await create_checkout(
        request=request_data,
        user_id=user.userId, # type: ignore
        email=user.email,
        first_name=user.firstName,
        last_name=user.lastName,
    )
    return session


# Compatibility wrapper.
@router.post("/create-payment-link")
async def create_payment_link(payment: PaymentLink, dep=Depends(verify_token)):
    checkout_request = CheckoutCreateRequest(
        bundleId=payment.bundle_id,
        countryCode="NG",
        provider=PaymentProvider.flutterwave,
    )
    user = await get_user_details_with_accessToken(token=dep["accessToken"])
    if not user:
        raise HTTPException(status_code=401, detail="User details not found or unauthorized")
    session = await create_checkout(
        request=checkout_request,
        user_id=user.userId, # type: ignore
        email=user.email,
        first_name=user.firstName,
        last_name=user.lastName,
    )
    return {
        "link": session.checkoutUrl,
        "tx_ref": session.txRef,
        "provider": session.provider,
    }


@router.post("/pay-chapter")
async def make_payment_for_book(payment: ChapterPayment, dep=Depends(verify_token)):
    user_details = await get_user_details_with_accessToken(token=dep["accessToken"])
    if not user_details:
        raise HTTPException(status_code=401, detail="User details not found or unauthorized")

    return await pay_for_chapter(
        user_details.userId, # type: ignore
        bundle_id=payment.bundle_id,
        chapter_id=payment.chapterId,
    )


@router.post("/webhooks/flutterwave")
async def flutterwave_webhook(request: Request):
    payload = await request.body()
    return await process_webhook(
        provider=PaymentProvider.flutterwave,
        raw_body=payload,
        headers={k.lower(): v for k, v in request.headers.items()},
    )


@router.post("/webhooks/paystack")
async def paystack_webhook(request: Request):
    payload = await request.body()
    return await process_webhook(
        provider=PaymentProvider.paystack,
        raw_body=payload,
        headers={k.lower(): v for k, v in request.headers.items()},
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    return await process_webhook(
        provider=PaymentProvider.stripe,
        raw_body=payload,
        headers={k.lower(): v for k, v in request.headers.items()},
    )


# Legacy compatibility endpoint.
@router.post("/webhook")
async def legacy_flutterwave_webhook(request: Request):
    payload = await request.body()
    return await process_webhook(
        provider=PaymentProvider.flutterwave,
        raw_body=payload,
        headers={k.lower(): v for k, v in request.headers.items()},
    )
