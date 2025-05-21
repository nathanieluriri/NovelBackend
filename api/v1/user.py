from fastapi import APIRouter, HTTPException,Depends
from schemas.user_schema import NewUserBase, NewUserCreate,NewUserOut,OldUserBase,OldUserOut,OldUserCreate
from services.user_service import register_user,verify_google_access_token,login_credentials,login_google,generate_refresh_tokens
from schemas.tokens_schema import TokenOut,refreshTokenRequest
from security.auth import verify_admin_token,verify_token,verify_token_and_refresh_token
from repositories.tokens_repo import delete_refresh_token
router = APIRouter()

@router.post("/sign-up", response_model=NewUserOut)
async def register(user: NewUserBase):
    if user.provider=="google":
        other_values = verify_google_access_token(google_access_token=user.googleAccessToken)
        if other_values:
            user = NewUserCreate(firstName=other_values['firstName'],email=other_values['email'],lastName=other_values['lastName'],avatar=other_values['avatar'],provider=user.provider,password="None",googleAccessToken=None)
    elif user.provider=="credentials":
        user = NewUserCreate(**user.model_dump())
    try:
        new_user = await register_user(user)
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/sign-in",response_model=TokenOut)
async def login(user_data:OldUserBase):
    try:
        if user_data.provider=="credentials":
            data = await login_credentials(user_data=user_data)
            response = TokenOut(userId=data.userId,accesstoken=data.accessToken,refreshtoken=data.refreshToken)
            return response
        elif user_data.provider=="google":
            data = await login_google(user_data=user_data)
            response = TokenOut(userId=data.userId,accesstoken=data.accessToken,refreshtoken=data.refreshToken)
            return response
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

@router.post("/get-details")
async def get_user_details():
    return {"message":"success"}

@router.post("/protected-member",dependencies=[Depends(verify_token)])
async def protected_route():
    return {"message":"success"} 

@router.post("/protected-admin",dependencies=[Depends(verify_admin_token)])
async def protected_route_admin():
    return {"message":"success"} 