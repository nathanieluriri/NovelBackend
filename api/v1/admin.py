from fastapi import APIRouter, HTTPException,Depends, Request,Body
from schemas.admin_schema import NewAdminCreate, AdminBase,NewAdminOut,DefaultAllowedAdminCreate,AdminUpdate
from services.admin_services import get_admin_details_with_accessToken_service,register_admin_func,login_admin_func,invitation_process,change_of_admin_password_flow1,change_of_admin_password_flow2, setup_default_admin,update_admin,get_all_admin_details
from services.email_service import get_location,send_invitation
from schemas.tokens_schema import TokenOut,refreshTokenRequest
from schemas.email_schema import VerificationRequest
from security.auth import verify_admin_token,verify_token,verify_token_and_refresh_token
from security.admin_otp import verify_otp
from repositories.tokens_repo import delete_refresh_token
from dotenv import load_dotenv
import os
from pydantic import BaseModel,EmailStr
from typing import List


load_dotenv()
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL")


router = APIRouter()

class invitedPersonsEmail(BaseModel):
    email:EmailStr

@router.on_event("startup")
async def startup_app():
    default_admin = DefaultAllowedAdminCreate(email=DEFAULT_ADMIN_EMAIL)
    await setup_default_admin(admin_details=default_admin)
    print("Admin Setup complete")
     

@router.post("/invite",dependencies=[Depends(verify_admin_token)])
async def invite_new_admin(invitedPersonsEmail:invitedPersonsEmail,accessToken:str = Depends(verify_admin_token)):
    try:
        await invitation_process(invitedEmail=invitedPersonsEmail.email,accessToken=accessToken['accessToken'])
        return {"message":"success"}
    except Exception as e:
        raise e

@router.post("/sign-up", response_model=NewAdminOut)
async def register_admin(user: NewAdminCreate,request:Request):
    try:
        location_details = await get_location(request=request,clientType="admin",user_id="ss")
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
        location_details = await get_location(request=request,clientType="admin",user_id="ss")
   except:
        raise 
   try:
       
        user= await login_admin_func(user_data=user_data,location=location_details)
        return user
   except Exception as e:
        print("login function",e)
        raise 

@router.post('/verify/')
async def verify_otp_and_activate_accessToken(verify:VerificationRequest):
    try:
        result =await verify_otp(accessToken=verify.access_token,otp=verify.otp)
        return {"message":result}
    except Exception as e:
        print
        raise 


@router.post("/refresh")
async def refresh_access_token(refreshObj:refreshTokenRequest, dep=Depends(verify_token_and_refresh_token)):
    result = await delete_refresh_token(refreshToken=refreshObj.refreshToken)
    if result:
        return dep
    else:
        raise HTTPException(status_code=404,detail="Refresh Token is Invalid")


@router.post("/initiate/change-password")
async def initiate_change_of_user_password_process(email= Body(title="email",description="Enter your email",alias="email")):
    try:
        await change_of_admin_password_flow1(email=email['email'])
        return {"message":"Success"}
    except Exception as e:
        raise e

@router.post("/conclude/change-password")
async def conclude_change_of_user_password_process(email=  Body(title="email",description="Enter your email",alias="email"),otp =  Body(title="otp",description="Enter your otp",alias="otp"),password=  Body(title="password",description="Enter your password",alias="password")):
    result = await change_of_admin_password_flow2(email=email,otp=otp,password=password)
    return {"message": result}


@router.get("/details",response_model_exclude_none=True,dependencies=[Depends(verify_token)])
async def get_admin_details(accessToken:str=Depends(verify_token) )->NewAdminOut:
    user= await get_admin_details_with_accessToken_service(token=accessToken['accessToken'])
    if user:
        return user
    else:
        raise HTTPException(status_code=404,detail="Details not found")


@router.get("/all/details",response_model_exclude_none=True,dependencies=[Depends(verify_token)])
async def get_admin_details(accessToken:str=Depends(verify_token) )->List[NewAdminOut]:
    user= await get_all_admin_details()
    if user:
        return user
    else:
        raise HTTPException(status_code=404,detail="Details not found")




@router.patch("/update",response_model_exclude_none=True,dependencies=[Depends(verify_token)])
async def update(update:AdminUpdate,accessToken:str=Depends(verify_token))->NewAdminOut:
    try:
        await update_admin(token=accessToken['accessToken'],update=update)
        user= await get_admin_details_with_accessToken_service(token=accessToken['accessToken'])
        if user:
            return user
        
    except Exception as e:
        raise e