from fastapi import APIRouter, HTTPException,Depends
from schemas.user_schema import NewUserBase, NewUserCreate,NewUserOut
from services.user_service import register_user,verify_google_access_token
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sign-in",response_model=TokenOut,dependencies=[Depends(verify_admin_token)])
def login():
    return {"user": "authenticated_user"}



@router.get("/refresh",response_model=TokenOut)
def login():
    return {"user": "authenticated_user"}


