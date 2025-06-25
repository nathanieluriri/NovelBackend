from repositories.payment_repo import create_payment_bundle,get_all_payment_bundles,update_payment_bundle,delete_payment_bundle
from services.payment_service import createLink,record_purchase_of_stars,pay_for_chapter
from services.chapter_services import fetch_chapter_with_chapterId
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
    
    

 
 
@router.post("/pay-chapter")
async def create_payment_link(payment: ChapterPayment, dep=Depends(verify_token)):
    try:
        payment_bundle = await get_payment_bundle(bundle_id=payment.bundle_id)
        if not payment_bundle:
            raise HTTPException(status_code=404, detail="Payment bundle not found")

        user_details = await get_user_details_with_accessToken(token=dep['accessToken'])
        if not user_details:
            raise HTTPException(status_code=401, detail="User details not found or unauthorized")

        chapter = await fetch_chapter_with_chapterId(chapterId=payment.chapterId)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        paid_chapter = pay_for_chapter(
            user_details.userId,
            bundle_id=payment_bundle.id,
            chapter_id=chapter.id
        )

        return {"message": "Payment successful", "chapter": paid_chapter}

    except HTTPException:
        raise  # re-raise HTTP exceptions directly
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

 
@router.post("/webhook")
async def flutterwave_webhook(request: Request, verif_hash: str = Header(None)):

    try:
        if verif_hash is None or verif_hash != FLW_WEBHOOK_SECRET_HASH:
         
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
            parts = dict(part.split(":") for part in tx_ref.split("|"))
            payload["uid"] = parts.get("uid")
            payload["timestamp"] = parts.get("ts")
            payload["bid"] = parts.get("bid")
         
            data= {"status": "verified"}
            user_out= await record_purchase_of_stars(userId=payload["uid"],tx_ref=tx_ref,bundleId=payload["bid"])
            return JSONResponse(status_code=200,content=data)

     
        return {"status": "ignored"}

    except Exception as e:


        raise  # Re-raise so FastAPI still throws the correct error

     