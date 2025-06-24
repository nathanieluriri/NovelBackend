from repositories.payment_repo import create_payment_bundle,get_all_payment_bundles,update_payment_bundle,delete_payment_bundle
from services.payment_service import createLink,record_purchase_of_stars
from fastapi import APIRouter, HTTPException,Depends,Request, Header
from fastapi.responses import JSONResponse
from security.auth import verify_admin_token,verify_token,verify_any_token
import hmac
import hashlib
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
    
    
    
    
@router.patch("/update-payment-bundle/{bundleId}")
async def update_payment_bundle_route(bundleId:str,paymentBundle:PaymentBundlesUpdate):
    if len(bundleId) != 24:
        raise HTTPException(status_code=400, detail="bundleId must be exactly 24 characters long")

    try:
        FixedBundle = await update_payment_bundle(bundle_id=bundleId,update_data=paymentBundle)
        return JSONResponse(content={"message":FixedBundle}) 
    except:
        raise    
    
    
    
@router.delete("/delete-payment-bundle/{bundleId}")
async def delete_payment_bundle_route(bundleId:str):
    if len(bundleId) != 24:
        raise HTTPException(status_code=400, detail="bundleId must be exactly 24 characters long")

    try:
        FixedBundle = await delete_payment_bundle(bundle_id=bundleId)
        
        return JSONResponse(content={"message":FixedBundle}) 
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
    
    

 

WEBHOOK_LOG_URL = "https://webhook.site/aa908af2-2986-4ec1-b4aa-eb7d28c67dae"

@router.post("/webhook")
async def flutterwave_webhook(request: Request, verif_hash: str = Header(None)):
    import requests as r
    import json
    raw_body = await request.body()
    log_payload = {
        "status": "start",
        "error": None,
        "tx_ref": None,
        "step": "verifying",
    }

    try:
        if verif_hash is None or verif_hash != FLW_WEBHOOK_SECRET_HASH:
            log_payload["status"] = "rejected"
            log_payload["error"] = "Invalid signature"
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

        # Parse payload
        payload = await request.json()
        event = payload.get("event")
        data = payload.get("data", {})

        if (
            event == "charge.completed" and
            data.get("status") == "successful"
        ):
            tx_ref = data.get("tx_ref")
            log_payload["tx_ref"] = tx_ref
            parts = dict(part.split(":") for part in tx_ref.split("|"))
            payload["uid"] = parts.get("uid")
            payload["timestamp"] = parts.get("ts")
            payload["bid"] = parts.get("bid")
            log_payload["status"] = "verified"
            log_payload["step"] = "processed"
            log_payload["data"] = payload
            data= {"status": "verified"}
            record_purchase_of_stars.delay(userId=payload["uid"],tx_ref=tx_ref,bundleId=payload["bid"])
            return JSONResponse(status_code=200,content=data)

        log_payload["status"] = "ignored"
        log_payload["step"] = "not_matching_criteria"

        return {"status": "ignored"}

    except Exception as e:
        log_payload["status"] = "error"
        log_payload["error"] = str(e)

        raise  # Re-raise so FastAPI still throws the correct error

    finally:
        # Log to webhook.site no matter what
        try:
            r.post(
                url=WEBHOOK_LOG_URL,
                data=json.dumps(log_payload),
                headers={"Content-Type": "application/json"}
            )
        except Exception as log_err:
            print("Failed to log to webhook.site:", log_err)
