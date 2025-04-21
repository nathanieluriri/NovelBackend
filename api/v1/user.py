from fastapi import APIRouter, HTTPException,Depends
from schemas.user_schema import NewUserBase, NewUserCreate,NewUserOut,OldUserBase,OldUserOut,OldUserCreate
from services.user_service import register_user,verify_google_access_token,login_credentials,login_google
from schemas.tokens_schema import TokenOut
from security.auth import verify_admin_token
router = APIRouter()

@router.post("/sign-up", response_model=NewUserOut)
async def register(user: NewUserBase):
    if user.provider=="google":
        other_values = verify_google_access_token(google_access_token=user.googleAccessToken)
        user = NewUserCreate(firstName=other_values['firstName'],email=other_values['email'],lastName=other_values['lastName'],avatar=other_values['avatar'],provider=user.provider,)
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
            print(data)
            response = TokenOut(userId=data.userId,accesstoken=data.accessToken,previousAccessToken=data.accessToken,refreshtoken=data.accessToken)
            return response
        elif user_data.provider=="google":
            data = await login_google(user_data=user_data)
            response = TokenOut(userId=data.userId,accesstoken=data.accessToken,previousAccessToken=data.accessToken,refreshtoken=data.accessToken)
            return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


    



@router.get("/refresh",response_model=TokenOut)
def refresh_access_token():
    return {"user": "authenticated_user"}


