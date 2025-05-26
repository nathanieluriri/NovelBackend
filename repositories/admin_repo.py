from core.database import db
from schemas.admin_schema import AdminBase,NewAdminCreate,NewAdminOut,AllowedAdminCreate,DefaultAllowedAdminCreate
from schemas.email_schema import ClientData
from bson import ObjectId

async def get_admin_by_email(email: str)->NewAdminOut|None:
    admin = await db.admins.find_one({"email": email})
    try:
        newAdmin = NewAdminOut(**admin)
        print(newAdmin)
        return newAdmin
    except TypeError:
        print("no admin user for the email")
        return None
    
async def get_admin_by_email_return_dict(email: str)->dict:
    admin = await db.admins.find_one({"email": email})
    try:
        return admin
    except TypeError:
        print("no admin user for the email")
        return None
        
async def create_admin(user_data: NewAdminCreate):
    user = user_data.model_dump()
    result = await db.admins.insert_one(user)
    created_user = await db.admins.find_one({"_id": result.inserted_id})
    return created_user


async def create_allowed_admin(user_data: AllowedAdminCreate):
    user = user_data.model_dump()
    result = await db.AllowedAdmins.insert_one(user)
    created_user = await db.AllowedAdmins.find_one({"_id": result.inserted_id})
    return created_user


async def delete_admin_by_email_and_provider(email: str,provider:str):
    return await db.admins.delete_one({"email": email})



async def get_allowd_admin_emails(email: str):
    admin = await db.AllowedAdmins.find_one({"email": email})
    if not admin:
        print("this email isn't allowed to register as an admin")
        return False

    try:
        newAdmin = NewAdminOut(**admin)
        return True
    except TypeError as e:
        print("TypeError while parsing admin data:", e)
        return False

        
        
async def create_email_list_for_admins(email: str):
    user_data = {}
    user_data['email']=email
    result = await db.AllowedAdmins.insert_one(user_data)
    created_user = await db.AllowedAdmins.find_one({"_id": result.inserted_id})
    return created_user



async def get_admin_details_with_accessToken(accessToken:str):
    accessToken_doc = await db.accessToken.find_one({"_id": ObjectId(accessToken)})
    admin_doc = await db.admins.find_one({"_id":ObjectId(accessToken_doc['userId'])})
    return admin_doc
    
    
async def get_location_details_for_admin(user_id:str)->ClientData:
    try:
        location_docs = await db.LoginAttempts.find_one({"userId": user_id})
        if location_docs:
            await db.LoginAttempts.find_one_and_delete({"userId": user_id})
            locationObj= ClientData(**location_docs)
            return locationObj
        else:
            return None
    except Exception as e:
        print(e)
        raise e
    
    
    
async def replace_password_admin(userId: str, hashedPassword: str):
    await db.admins.find_one_and_update(
        filter={"_id": ObjectId(userId)},
        update={"$set": {"password": hashedPassword}}
    )
    
    
    
async def create_default_admin(user_data: DefaultAllowedAdminCreate):
    user = user_data.model_dump()

    already_here =await db.AllowedAdmins.find_one({"email": user['email']})
    if already_here:
        return 0
    else:

        result = await db.AllowedAdmins.insert_one(user)
        created_user = await db.AllowedAdmins.find_one({"_id": result.inserted_id})
        return created_user



async def update_admin_profile(userId: str, update: dict):
    await db.admins.find_one_and_update(
        filter={"_id": ObjectId(userId)},
        update={"$set": update}
    )
    