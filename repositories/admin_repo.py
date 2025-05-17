from core.database import db
from schemas.admin_schema import NewAdminBase,NewAdminCreate,NewAdminOut
from bson import ObjectId

async def get_admin_by_email(email: str):
    admin = await db.admins.find_one({"email": email})
    try:
        newAdmin = NewAdminOut(**admin)
        return newAdmin
    except TypeError:
        print("no admin user for the email")
        return None
        
async def create_admin(user_data: NewAdminCreate):
    user = user_data.model_dump()
    result = await db.admins.insert_one(user)
    created_user = await db.admins.find_one({"_id": result.inserted_id})
    return created_user


async def delete_admin_by_email_and_provider(email: str,provider:str):
    return await db.admins.delete_one({"email": email})



async def get_allowd_admin_emails(email: str):
    admin = await db.AllowedAdmins.find_one({"email": email})
    try:
        newAdmin = NewAdminOut(**admin)
        return newAdmin
    except TypeError:
        print("this email isn't allowed to register the email")
        return None
        
        
        
async def create_email_list_for_admins(email: str):
    user_data = {}
    user_data['email']=email
    result = await db.AllowedAdmins.insert_one(user_data)
    created_user = await db.AllowedAdmins.find_one({"_id": result.inserted_id})
    return created_user
