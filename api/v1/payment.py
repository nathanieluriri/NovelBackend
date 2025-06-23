from repositories.payment_repo import create_payment_bundle,get_all_payment_bundles,update_payment_bundle
from services.payment_service import createLink
from fastapi import APIRouter, HTTPException,Depends
from security.auth import verify_admin_token,verify_token,verify_any_token
import hmac
import hashlib
from fastapi import  Request, Header, HTTPException
from schemas.payments_schema import *
from services.user_service import get_user_details_with_accessToken
from repositories.payment_repo import get_payment_bundle
router = APIRouter()

@router.post("/create-payment-bundle",dependencies=[Depends(verify_admin_token)])
async def create_payment_bundle_route(paymentBundle:PaymentBundles)->PaymentBundlesOut:
    try:
        newBundle = await create_payment_bundle(bundle=paymentBundle)
        return newBundle
    except:
        raise    
    
    
@router.get("/get-payment-bundles",dependencies=[Depends(verify_any_token)])
async def get_payment_bundle_route()->List[PaymentBundlesOut]:
    try:
        AllBundles = await get_all_payment_bundles()
        return AllBundles
    except:
        raise    
    
    
    
    
@router.patch("/update-payment-bundles/{bundleId}")
async def get_payment_bundle_route(bundleId:str,paymentBundle:PaymentBundlesUpdate)->List[PaymentBundlesOut]:
    if len(bundleId) != 24:
        raise HTTPException(status_code=400, detail="bundleId must be exactly 24 characters long")

    try:
        FixedBundle = await update_payment_bundle(bundle_id=bundleId,update_data=paymentBundle)
        return FixedBundle
    except:
        raise    
    
    
    
    

    
@router.post("/create-payment-link")
async def create_payment_link(payment:PaymentLink,dep=Depends(verify_token)):
    try:
        paymentBundle  = await get_payment_bundle(bundle_id=payment.bundle_id)
        if paymentBundle:
            userDetails=await get_user_details_with_accessToken(token=dep['accessToken'])
            if userDetails:
                newLink = createLink(bundle_description=paymentBundle.description,bundle_id=payment.bundle_id,userId=userDetails.userId,email=userDetails.email,amount=str(paymentBundle.amount),firstName=userDetails.firstName,lastName=userDetails.lastName)
                return newLink
    except:
        raise    
    
    
import requests as r
@router.post("/webhook")
async def flutterwave_webhook(request: Request, verif_hash: str = Header(None)):
    # 1. Get raw body bytes
    
    import json
    raw_body = await request.body()

    # 2. Compute HMAC SHA256 using your secret hash
    computed_hash = hmac.new(
        FLW_WEBHOOK_SECRET_HASH.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    # 3. Compare computed hash with the header
    if computed_hash != verif_hash:
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    # 4. Parse payload and continue your logic
    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data", {})

    if event == "charge.completed" and data.get("status") == "successful" and data.get("payment_type") == "bank_transfer":
        tx_ref = data.get("tx_ref")
        parts = dict(part.split(":") for part in tx_ref.split("|"))
        user_id = parts.get("uid")
        timestamp = parts.get("ts")
        bundle_id = parts.get("bid")
        webhook_url = "https://webhook.site/aa908af2-2986-4ec1-b4aa-eb7d28c67dae"
        payload['uid']=user_id
        payload['timestamp']=timestamp
        payload['bid']=bundle_id
        raw_body = json.dumps(payload).encode()
        r.post(
            url=webhook_url,
            data= raw_body
        )
        return {"status": "verified"}
    
    return {"status": "ignored"}
