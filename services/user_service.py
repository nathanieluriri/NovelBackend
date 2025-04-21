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
    if response.get('error',None)!=None:
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
    new_user.accessToken= generate_member_access_tokens(new_user.userId)
    new_user.refreshToken= generate_refresh_tokens(userId=new_user.userId,accessToken=new_user.accessToken)
    return new_user




async def login_credentials(user_data:OldUserBase):
    existing = await get_user_by_email_and_provider(email=user_data.email,provider="credentials")
    if existing:
        if existing.get("password",None):
            if check_password(password=user_data.password,hashed=existing.get("password")):
                "success"
                existing['accessToken']= await generate_member_access_tokens(existing['userId'])
                existing['refreshToken']=await generate_refresh_tokens(userId=existing['userId'],accessToken=existing['accessToken'])
                
                return OldUserOut(**existing)
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Password Incorrect")
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail="Password wasn't provided")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")        


async def login_google(user_data:OldUserBase):
    existing = await get_user_by_email_and_provider(email=user_data.email,provider="credentials")
    if existing:
        details = verify_google_access_token(user_data.accessToken)
        if details['email']==user_data.email:
            "success"
            existing['accessToken']= await generate_member_access_tokens(existing['userId'])
            existing['refreshToken']=await generate_refresh_tokens(userId=existing['userId'],accessToken=existing['accessToken'])
            return OldUserOut(**existing)
        else:raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found")