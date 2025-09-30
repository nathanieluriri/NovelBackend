from repositories.user_repo import get_user_by_email, create_user,get_user_by_email_and_provider,get_user_by_userId,replace_password,update_user_profile
from repositories.tokens_repo import get_access_tokens,delete_all_tokens_with_user_id
from schemas.user_schema import NewUserCreate,UserOut,OldUserBase,OldUserCreate,OldUserOut,UserUpdate
from fastapi import HTTPException,status
from security.hash import check_password,hash_password
from security.tokens import generate_member_access_tokens,generate_refresh_tokens
from security.user_otp import generate_otp, verify_otp, send_otp_user

def verify_google_access_token(google_access_token:str):
    import requests

    url = "https://www.googleapis.com/oauth2/v3/userinfo"

    payload = {}
  
    headers = {
    'Authorization': f'Bearer {google_access_token}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    response = response.json()
    if response.get('error',None)!=None:
        raise HTTPException(status_code=401,detail="Invalid Google Access Token")
        return None
    else:
        avatar = response.get("picture")
        firstName= response.get("given_name")
        lastName= response.get("family_name")
        email= response.get("email")
        return {"avatar":avatar,"firstName":firstName,"lastName":lastName,"email":email,"google_access_token" :google_access_token}



async def register_user(user_data: NewUserCreate):
    existing = await get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="User already exists")
    new_user =await create_user(user_data)
    new_user = UserOut(**new_user)
    accessToken= await generate_member_access_tokens(new_user.userId)
    new_user.accessToken=accessToken.accesstoken
    refreshToken= await generate_refresh_tokens(userId=new_user.userId,accessToken=new_user.accessToken)
    
    
    new_user.refreshToken=refreshToken.refreshtoken
    return new_user




async def login_credentials(user_data:OldUserBase):
    existing = await get_user_by_email_and_provider(email=user_data.email,provider="credentials")
    if existing:
        if existing.get("password",None)!=None:
            hashed=existing.get("password")
            regular=user_data.password
            
            if check_password(regular,hashed=hashed):
                
                accessToken=await generate_member_access_tokens(str(existing['_id']))
                existing['accessToken']= accessToken.accesstoken
                
                refreshToken=await generate_refresh_tokens(userId=str(existing['_id']),accessToken=accessToken.accesstoken)
                
                existing['refreshToken']= refreshToken.refreshtoken
                
                return OldUserOut(**existing)
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Password Incorrect")
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail="Password wasn't provided")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")        


async def login_google(user_data:OldUserBase):
    existing = await get_user_by_email_and_provider(email=user_data.email,provider="google")
    print(existing)
    if existing:
        details = verify_google_access_token(user_data.googleAccessToken)
        if details['email']==user_data.email:
            print(details)
            accessToken =await generate_member_access_tokens(str(existing['_id']))
            existing['accessToken']= accessToken.accesstoken
            refreshToken =await generate_refresh_tokens(userId=str(existing['_id']),accessToken=existing['accessToken'])
            existing['refreshToken']= refreshToken.refreshtoken
            return OldUserOut(**existing)
        else:raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Invalid User Login")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")
    
    
    
async def get_user_details_with_accessToken(token:str)->UserOut:
    tokenOut = await get_access_tokens(accessToken=token)
    if tokenOut:
        userDetails = await get_user_by_userId(userId=tokenOut.userId)
        if userDetails:
            return UserOut(**userDetails)
        
        
async def change_of_user_password_flow1(email):
    if await get_user_by_email(email=email):
        otp = generate_otp(email=email)
        await send_otp_user(otp=otp,user_email=email)
    else:
        raise HTTPException(status_code=404,detail="User Doesn't exist")
    
    
    
async def change_of_user_password_flow2(email,otp,password):
    isValid = await verify_otp(email=email,otp=otp)
    if isValid:
        hashed_password= hash_password(password=password)
        user = await get_user_by_email(email=email)
        await replace_password(userId=str(user['_id']),hashedPassword=hashed_password)
        
        await delete_all_tokens_with_user_id(userId=str(user['_id']))
        return True
    elif isValid==False:
        return False
        
async def update_user(token:str,update:UserUpdate):
    try:
        user= await get_user_details_with_accessToken(token=token)
        if user:
            await update_user_profile(userId=user.userId,update=update.model_dump(exclude=None))
        else:
            raise HTTPException(status_code=404,detail="User Doesn't exist")
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"{e}")