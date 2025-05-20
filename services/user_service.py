from repositories.user_repo import get_user_by_email, create_user,get_user_by_email_and_provider
from schemas.user_schema import NewUserCreate,NewUserOut,OldUserBase,OldUserCreate,OldUserOut
from fastapi import HTTPException,status
from security.hash import check_password
from security.tokens import generate_member_access_tokens,generate_refresh_tokens


def verify_google_access_token(google_access_token:str):
    import requests

    url = "https://www.googleapis.com/oauth2/v3/userinfo"

    payload = {}
  
    headers = {
    'Authorization': f'Bearer {google_access_token}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    response = response.json()
    print(response)
    if response.get('error',None)!=None:
        raise HTTPException(status_code=401,detail="Invalid Google Access Token")
        return None
    else:
        avatar = response.get("picture")
        firstName= response.get("given_name")
        lastName= response.get("family_name")
        email= response.get("email")
        return {"avatar":avatar,"firstName":firstName,"lastName":lastName,"email":email}



async def register_user(user_data: NewUserCreate):
    existing = await get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="User already exists")
    new_user =await create_user(user_data)
    new_user = NewUserOut(**new_user)
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
                print("refresh token ", refreshToken.refreshtoken)
                
                return OldUserOut(**existing)
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Password Incorrect")
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail="Password wasn't provided")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")        


async def login_google(user_data:OldUserBase):
    existing = await get_user_by_email_and_provider(email=user_data.email,provider="google")
    if existing:
        details = verify_google_access_token(user_data.accessToken)
        if details['email']==user_data.email:
            accessToken =await generate_member_access_tokens(str(existing['_id']))
            existing['accessToken']= accessToken.accesstoken
            refreshToken =await generate_refresh_tokens(userId=str(existing['_id']),accessToken=existing['accessToken'])
            existing['refreshToken']= refreshToken.refreshtoken
            print(existing)
            return OldUserOut(**existing)
        else:raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")