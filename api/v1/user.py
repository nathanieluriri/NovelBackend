from fastapi import APIRouter, HTTPException
from schemas.user_schema import UserCreate, UserOut
from services.user_service import register_user

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register(user: UserCreate):
    try:
        new_user = await register_user(user)
        return new_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
