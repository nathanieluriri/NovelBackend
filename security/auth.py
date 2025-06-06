# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from security.tokens import validate_admin_accesstoken,generate_refresh_tokens,generate_member_access_tokens, validate_member_accesstoken, validate_refreshToken,validate_member_accesstoken_without_expiration,generate_admin_access_tokens
from security.encrypting_jwt import decode_jwt_token
from repositories.tokens_repo import delete_access_token,update_admin_access_tokens
from schemas.tokens_schema import refreshedToken,accessTokenOut


token_auth_scheme = HTTPBearer()
async def verify_token(token: str = Depends(token_auth_scheme)):
    result = await validate_member_accesstoken(accessToken=token.credentials)
    
    if result==None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    else:
        decoded_access_token = await decode_jwt_token(token=token.credentials)
        return decoded_access_token
            
        
        
        
async def verify_token_and_refresh_token(token: str = Depends(token_auth_scheme)):
    decodedT= await decode_jwt_token(token=token.credentials)
    if decodedT['role']=="member":
        result = await validate_member_accesstoken_without_expiration(accessToken=token.credentials)
        
        accessTokenObj= await generate_member_access_tokens(userId=result.userId)
        
        refreshTokenObj = await generate_refresh_tokens(userId=result.userId,accessToken=accessTokenObj.accesstoken)
        await delete_access_token(result.accesstoken)
        refreshedTokens = refreshedToken(userId=result.userId,refreshToken=refreshTokenObj.refreshtoken,accessToken=accessTokenObj.accesstoken)
        if result==None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        else:
            return refreshedTokens
    elif decodedT['role']=="admin":
        result = await validate_admin_accesstoken(accessToken=str(token.credentials))
        if result =="inactive":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You Can't Make Use of an Inactive AccessToken"
            )
        elif type(result) ==type(accessTokenOut(userId="sa",accesstoken="sa",)):
            accessTokenObj = await generate_admin_access_tokens(userId=result.userId)
            NewDecodedT = await decode_jwt_token(token=accessTokenObj.accesstoken)
            
            await update_admin_access_tokens(token=NewDecodedT['accessToken'])
            refreshTokenObj = await generate_refresh_tokens(userId=result.userId,accessToken=accessTokenObj.accesstoken)
            await delete_access_token(result.accesstoken)
            refreshedTokens = refreshedToken(userId=result.userId,refreshToken=refreshTokenObj.refreshtoken,accessToken=accessTokenObj.accesstoken)
            return refreshedTokens
        elif result==None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Token"
            )
           
async def verify_admin_token(token: str = Depends(token_auth_scheme)):
    print("here")
    result = await validate_admin_accesstoken(accessToken=str(token.credentials))
    print("here")
    if result==None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )
    elif result=="inactive":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin Token hasn't been activated"
        )
    elif type(result)==type(accessTokenOut(userId="1",accesstoken="2")):
        
        decoded_access_token = await decode_jwt_token(token=token.credentials)
        return decoded_access_token
