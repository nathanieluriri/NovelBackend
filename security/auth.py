# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
token_auth_scheme = HTTPBearer()

def verify_token(token: str = Depends(token_auth_scheme)):
    print(token)
    if token.credentials != "secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
