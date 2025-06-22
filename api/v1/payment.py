from repositories.payment_repo import create_payment_bundle,get_all_payment_bundles,update_payment_bundle
from services.payment_service import createLink
from fastapi import APIRouter, HTTPException,Depends
from security.auth import verify_admin_token
from schemas.payments_schema import *

 
router = APIRouter()

@router.post("/create-payment-bundle")
async def create_payment_bundle_route(paymentBundle:PaymentBundles, dep=Depends(verify_admin_token))->PaymentBundlesOut:
    try:
        newBundle = await create_payment_bundle(bundle=paymentBundle)
        return newBundle
    except:
        raise    
    
    
@router.get("/get-payment-bundles")
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
async def create_payment_link(paymentBundle:PaymentBundles, dep=Depends(verify_admin_token))->PaymentBundlesOut:
    try:
        newBundle = await createLink(bundle=paymentBundle)
        return newBundle
    except:
        raise    
    