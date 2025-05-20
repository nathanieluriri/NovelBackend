from fastapi import APIRouter, HTTPException,Depends, Request
from schemas.admin_schema import NewAdminCreate, AdminBase,NewAdminOut
from services.admin_services import register_admin_func,login_admin_func
from services.email_service import get_location
from schemas.tokens_schema import TokenOut,refreshTokenRequest
from schemas.email_schema import VerificationRequest
from security.auth import verify_admin_token,verify_token,verify_token_and_refresh_token
from security.admin_otp import verify_otp
from repositories.tokens_repo import delete_refresh_token
router = APIRouter()


@router.post("/sign-up", response_model=NewAdminOut)
async def register_admin(user: NewAdminCreate,request:Request):
    try:
        location_details = await get_location(request=request)
    except:
        raise
    try:
        new_user = await register_admin_func(user,location=location_details)
        
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/sign-in",response_model=NewAdminOut)
async def login_admin(user_data:AdminBase,request:Request):
    try:
        location_details = await get_location(request=request)
        user= await login_admin_func(user_data=user_data,location=location_details)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/verify/')
async def verify_otp_and_activate_accessToken(verify:VerificationRequest):
    try:
        result =await verify_otp(accessToken=verify.access_token,otp=verify.otp)
        return {"message":result}
    except Exception as e:
        raise e


@router.post("/refresh")
async def refresh_access_token(refreshObj:refreshTokenRequest, dep=Depends(verify_token_and_refresh_token)):
    result = await delete_refresh_token(refreshToken=refreshObj.refreshToken)
    if result:
        return dep
    else:
        raise HTTPException(status_code=404,detail="Refresh Token is Invalid")


@router.post("/protected-member",dependencies=[Depends(verify_token)])
async def protected_route():
    return {"message":"success"} 

@router.post("/protected-admin",dependencies=[Depends(verify_admin_token)])
async def protected_route_admin():
    return {"message":"success"} 