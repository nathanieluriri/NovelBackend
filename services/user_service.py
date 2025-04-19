from repositories.user_repo import get_user_by_email, create_user
from schemas.user_schema import UserCreate

async def register_user(user_data: UserCreate):
    existing = await get_user_by_email(user_data.email)
    if existing:
        raise Exception("User already exists")
    return await create_user(user_data)
