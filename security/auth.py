# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
token_auth_scheme = HTTPBearer()
from security.tokens import validate_admin_accesstoken,generate_refresh_tokens,generate_member_access_tokens, validate_member_accesstoken, validate_refreshToken,validate_member_accesstoken_without_expiration
from repositories.tokens_repo import delete_access_token
from schemas.tokens_schema import refreshedToken

async def verify_token(token: str = Depends(token_auth_scheme)):
    result = await validate_member_accesstoken(accessToken=token.credentials)
    
    if result==None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    
        
        
        
async def verify_token_and_refresh_token(token: str = Depends(token_auth_scheme)):
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
    
        



def verify_admin_token(token: str = Depends(token_auth_scheme)):
    print(token)
    if token.credentials != "secret-token-admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )
