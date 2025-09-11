from fastapi import APIRouter, HTTPException,Depends, Body,Path
from schemas.user_schema import Provider,UserOutChapterDetails, NewUserBase, NewUserCreate,NewUserOut,OldUserBase,OldUserOut,OldUserCreate,UserUpdate,UserStatus
from services.user_service import register_user,verify_google_access_token,login_credentials,login_google,get_user_details_with_accessToken,change_of_user_password_flow1,change_of_user_password_flow2,update_user
from schemas.tokens_schema import TokenOut,refreshTokenRequest
from services.admin_services import get_all_user_details,update_user_details,get_one_user_details
from security.auth import verify_admin_token,verify_token,verify_token_and_refresh_token
from repositories.tokens_repo import delete_refresh_token
router = APIRouter()

@router.post("/sign-up", response_model=NewUserOut)
async def register(user: NewUserBase):
    if user.provider=="google":
        other_values = verify_google_access_token(google_access_token=user.googleAccessToken)
        if other_values:
            user = NewUserCreate(firstName=other_values['firstName'],email=other_values['email'],lastName=other_values['lastName'],avatar=other_values['avatar'],provider=user.provider,password="signed up with google",googleAccessToken=None)
            await user.model_async_validate()
    elif user.provider=="credentials":
        user = NewUserCreate(**user.model_dump())
        await user.model_async_validate()
    try:
        new_user = await register_user(user)
     
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/sign-in",response_model_exclude_none=True,response_model=OldUserOut)
async def login(user_data:OldUserBase):
    try:
        if user_data.provider=="credentials":
            data = await login_credentials(user_data=user_data)
        
            return data
        elif user_data.provider=="google":
            data = await login_google(user_data=user_data)
           
            return data
        else:
            raise HTTPException(status_code=404,detail="Provider Not Recognized")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/refresh")
async def refresh_access_token(refreshObj:refreshTokenRequest, dep=Depends(verify_token_and_refresh_token)):
    result = await delete_refresh_token(refreshToken=refreshObj.refreshToken)
    if result:
        return dep
    else:
        raise HTTPException(status_code=404,detail="Refresh Token is Invalid")


@router.get("/details",response_model_exclude_none=True,dependencies=[Depends(verify_token)])
async def get_user_details(accessToken:str=Depends(verify_token) )->NewUserOut:
    user= await get_user_details_with_accessToken(token=accessToken['accessToken'])
    if user:
        return user
    else:
        raise HTTPException(status_code=404,detail="Details not found")


@router.post("/initiate/change-password")
async def initiate_change_of_user_password_process(email= Body(title="email",description="Enter your email",alias="email")):
    try:
        await change_of_user_password_flow1(email=email['email'])
        return {"message":"Success"}
    except Exception as e:
        raise e

@router.post("/conclude/change-password")
async def conclude_change_of_user_password_process(email=  Body(title="email",description="Enter your email",alias="email"),otp =  Body(title="otp",description="Enter your otp",alias="otp"),password=  Body(title="password",description="Enter your password",alias="password")):
    result = await change_of_user_password_flow2(email=email,otp=otp,password=password)
    return {"message": result}

@router.patch("/update",response_model_exclude_none=True,dependencies=[Depends(verify_token)])
async def update(update:UserUpdate,accessToken:str=Depends(verify_token))->NewUserOut:
    try:
        await update_user(token=accessToken['accessToken'],update=update)
        user= await get_user_details_with_accessToken(token=accessToken['accessToken'])
        if user:
            return user
        
    except Exception as e:
        raise e
    
    
    
    
@router.get("/all/user-details",description="Requires admin Tokens",response_model_exclude_none=True,dependencies=[Depends(verify_admin_token)])
async def get_user_data():
    try:
        result  = await get_all_user_details()
       
        if result:
            return result
        
    except Exception as e:
        raise e
    
    
@router.get("/{userId}/user-details",response_model=UserOutChapterDetails,description="Requires admin Tokens",response_model_exclude_none=True,dependencies=[Depends(verify_admin_token)])
async def get_particular_user_data( userId: str = Path(..., description="The ID of the user whose status is to be updated."),):
    try:
        result  = await get_one_user_details(userId=userId)
       
        if result:
            return result
        
    except Exception as e:
        raise e
    
    
@router.patch("/{userId}/status/{new_status}",description="Requires admin Tokens",response_model_exclude_none=True,dependencies=[Depends(verify_admin_token)])
async def update_user_data(    userId: str = Path(..., description="The ID of the user whose status is to be updated."),
    new_status: UserStatus = Path(..., description="The new status for the user (active, suspended, or inactive).")):
    user = UserUpdate(status=new_status)
    try:
        result  = await update_user_details(updateData=user,userId=userId)
       
        if result:
            return result
        
    except Exception as e:
        raise e