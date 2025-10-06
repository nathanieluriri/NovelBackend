from repositories.admin_repo import get_admin_by_email, create_admin,get_allowd_admin_emails,get_admin_by_email_return_dict,get_admin_details_with_accessToken,replace_password_admin,create_default_admin, update_admin_profile,get_all_admins
from repositories.tokens_repo import delete_all_tokens_with_user_id,get_access_tokens
from repositories.user_repo import get_user_by_userId
from repositories.read_repo import get_particular_chapter_user_has_read
from repositories.chapter_repo import get_chapter_by_chapter_id
from schemas.admin_schema import NewAdminCreate,NewAdminOut,AdminBase,DefaultAllowedAdminCreate,AdminUpdate
from fastapi import HTTPException,status
from schemas.user_schema import UserOut,UserOutChapterDetails
from repositories.user_repo import get_all_users,update_user_profile
from typing import List
from schemas.email_schema import ClientData
from security.hash import check_password,hash_password
from security.tokens import generate_admin_access_tokens,generate_refresh_tokens
import os
from security.admin_otp import generate_otp,send_otp,send_otp_admin,verify_otp_admin,generate_otp_admin_password
from services.email_service import send_invitation
from dotenv import load_dotenv
load_dotenv()
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")

async def register_admin_func(user_data: NewAdminCreate,location:ClientData):
    proceed = await get_allowd_admin_emails(user_data.email)
    
    if proceed:
        existing = await get_admin_by_email(user_data.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="User already exists")
        new_user =await create_admin(user_data)
        
        new_user = NewAdminOut(**new_user)
        
        accessToken= await generate_admin_access_tokens(new_user.userId)
        location['userId']=new_user.userId
        new_user.accessToken=accessToken.accesstoken
        # generate and send otp
        otp = generate_otp(admin_access_token=new_user.accessToken)
        
        await send_otp(otp=otp,location=location,user_email=user_data.email)
        refreshToken= await generate_refresh_tokens(userId=new_user.userId,accessToken=new_user.accessToken)
        
        new_user.refreshToken=refreshToken.refreshtoken
        return new_user
    else:
        raise HTTPException(status_code=400, detail="This Email isn't Allowed To Register As An Admin")




async def login_admin_func(user_data:AdminBase,location:ClientData):
    existing = await get_admin_by_email_return_dict(email=user_data.email)
    
    if existing:
        
        if existing.get("password",None)!=None:
            hashed=existing.get("password")
            regular=user_data.password
            
            if check_password(regular,hashed=hashed):
                
                accessToken=await generate_admin_access_tokens(str(existing['_id']))
                print("accesstoken: ",accessToken)
                location['userId']=str(existing['_id'])
                print("location",location,end="\n")
                existing['accessToken']= accessToken.accesstoken 
                


                # generate and send otp 
                otp = generate_otp(admin_access_token=existing["accessToken"])
                print("otp",otp)
                
                # await send_otp(otp=otp,location=location,user_email=user_data.email)
                # TODO: Probably switch send_otp to something
                
                refreshToken=await generate_refresh_tokens(userId=str(existing['_id']),accessToken=accessToken.accesstoken)
                
                existing['refreshToken']= refreshToken.refreshtoken
                
                return NewAdminOut(**existing)
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Password Incorrect")
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail="Password wasn't provided")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")        
    
    
    
    
    
    
async def invitation_process(accessToken:str,invitedEmail):
    result = await get_admin_details_with_accessToken(accessToken=accessToken)
         
    await send_invitation(inviterEmail=result['email'],firstName=result['firstName'],invitedEmail=invitedEmail,lastName=result['lastName'])
    
    
    
    
    
    
    
    
    
async def change_of_admin_password_flow1(email):
    if await get_admin_by_email(email=email):
        otp = generate_otp_admin_password(email=email)
        await send_otp_admin(otp=otp,user_email=email)
    else:
        raise HTTPException(status_code=404,detail="Admin Doesn't exist")
    
    
    
async def change_of_admin_password_flow2(email,otp,password):
    isValid = await verify_otp_admin(email=email,otp=otp)
    if isValid:
        hashed_password= hash_password(password=password)
        admin = await get_admin_by_email(email=email)
        await replace_password_admin(userId=admin.userId,hashedPassword=hashed_password)
        
        await delete_all_tokens_with_user_id(userId=admin.userId)
        return True
    elif isValid==False:
        return False
        
    
    
async def setup_default_admin(admin_details:DefaultAllowedAdminCreate):
    result = await create_default_admin(user_data=admin_details)
    if result==0:
        return 0
    else:
        print("sending invite")
        await send_invitation(firstName="Default",lastName="Admin",invitedEmail=admin_details.email,inviterEmail=EMAIL_USERNAME)
        
        
        
        
async def get_admin_details_with_accessToken_service(token:str):
    adminOut = await get_admin_details_with_accessToken(accessToken=token)
    if adminOut:
        return NewAdminOut(**adminOut)
        
        
        
        
        
async def update_admin(token:str,update:AdminUpdate):
    try:
        admin= await get_admin_details_with_accessToken_service(token=token)
        if admin:
            await update_admin_profile(userId=admin.userId,update=update.model_dump(exclude=None))
        else:
            raise HTTPException(status_code=404,detail="User Doesn't exist")
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"{e}")
    
    
    
    
        
async def get_all_admin_details_service()->list:
    adminOut = await get_all_admins()
    if adminOut:
        return adminOut
        
        
        
async def get_all_user_details()->List[UserOut]:
    users = await get_all_users()
    usersOut =[]
    for user in users:
        usersOut.append(UserOut(**user))
    return usersOut


async def update_user_details(userId,updateData)->UserOut:
    users = await update_user_profile(userId=userId,update=updateData.model_dump())
    return UserOut(**users)

async def get_one_user_details(userId:str)->UserOutChapterDetails:
    user = await get_user_by_userId(userId=userId)
    if user:
        list_of_unlocked_chapters =user['unlockedChapters']
        chapterDetailsList=[]
        for chapter in list_of_unlocked_chapters:
            chapterDetails = await get_chapter_by_chapter_id(chapter)
            if chapterDetails:
                HasReadObj=await get_particular_chapter_user_has_read(userId=str(user['_id']),chapterId=chapter) 
                chapterDetails['hasRead']=HasReadObj.hasRead
                chapterDetailsList.append(chapterDetails)

        user['chapterDetails']=chapterDetailsList
        
        User =UserOutChapterDetails(**user)
        return User
            
