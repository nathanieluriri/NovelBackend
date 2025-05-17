from fastapi import APIRouter, HTTPException,Depends
from schemas.admin_schema import NewAdminCreate, NewAdminBase,NewAdminOut
from services.admin_services import register_admin_func,login_admin_func
from schemas.tokens_schema import TokenOut,refreshTokenRequest
from security.auth import verify_admin_token,verify_token,verify_token_and_refresh_token
from repositories.tokens_repo import delete_refresh_token
router = APIRouter()

@router.post("/sign-up", response_model=NewAdminOut)
async def register_admin(user: NewAdminCreate):
    try:
        new_user = await register_admin_func(user)
        
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/sign-in",response_model=NewAdminOut)
async def login_admin(user_data:NewAdminBase):
    try:
        pass
       
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


@router.post("/protected-member",dependencies=[Depends(verify_token)])
async def protected_route():
    return {"message":"success"} 

@router.post("/protected-admin",dependencies=[Depends(verify_admin_token)])
async def protected_route_admin():
    return {"message":"success"} 