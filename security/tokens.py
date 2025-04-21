from schemas.tokens_schema import refreshTokenOut,accessTokenOut,refreshTokenCreate,accessTokenCreate
from repositories.tokens_repo import add_access_tokens,add_refresh_tokens,get_access_tokens,get_refresh_tokens
from security.encrypting_jwt import create_jwt_admin_token,create_jwt_member_token,decode_jwt_token
from bson import errors,ObjectId
from fastapi import HTTPException,status

async def generate_member_access_tokens(userId)->accessTokenOut:
    
    try:
        obj_id = ObjectId(userId)
    except errors.InvalidId:
        raise   HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid User Id")    

    new_access_token = await add_access_tokens(token_data=accessTokenCreate(userId=userId))
    new_access_token.accesstoken = await create_jwt_member_token(token=new_access_token.accesstoken)
    
    return new_access_token

async def generate_admin_access_tokens(userId)->accessTokenOut:
    
    try:
        obj_id = ObjectId(userId)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid User Id")    # or raise an error / log it    

    new_access_token = await add_access_tokens(token_data=accessTokenCreate(userId=userId))
    new_access_token.accesstoken = await create_jwt_admin_token(token=new_access_token.accesstoken)
    return new_access_token
    
async def generate_refresh_tokens(userId,accessToken)->refreshTokenOut:

    try:
        obj_id = ObjectId(userId)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid User Id")    # or raise an error / log it    

    
    try:
        obj_id = ObjectId(accessToken)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Access Id")    # or raise an error / log it    

    new_refresh_token =await add_refresh_tokens(token_data=refreshTokenCreate(userId=userId,previousAccessToken=accessToken))
    return new_refresh_token


async def validate_refreshToken(refreshToken:str):
    try:
        obj_id = ObjectId(refreshToken)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Refresh Id")   # or raise an error / log it    

    refresh_token = await get_refresh_tokens(refreshToken=refreshToken)
    if refresh_token:
        new_refresh_token = await generate_refresh_tokens(userId=refresh_token.userId,accessToken=refresh_token.previousAccessToken)
        return new_refresh_token
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Refresh Id")
    



async def validate_member_accesstoken(accessToken:str):
    try:
        obj_id = ObjectId(accessToken)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Access Id")   # or raise an error / log it    

    decodedAccessToken = await decode_jwt_token(token=accessToken)
    if decodedAccessToken:
        validatedAccessToken= await get_access_tokens(accessToken=decodedAccessToken['accessToken'])
        if validatedAccessToken:
            return validatedAccessToken
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Refresh Id")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Refresh Id")
    
async def validate_admin_accesstoken(accessToken:str):
    try:
        obj_id = ObjectId(accessToken)
    except errors.InvalidId:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Access Id")   # or raise an error / log it    

    decodedAccessToken = await decode_jwt_token(token=accessToken)
    if decodedAccessToken:
        if decodedAccessToken['role']=="admin":
            validatedAccessToken= await get_access_tokens(accessToken=decodedAccessToken['accessToken'])
            if validatedAccessToken:
                return validatedAccessToken
            else:
                raise ""
        else:
            raise "" 
        
    else:
        raise ""