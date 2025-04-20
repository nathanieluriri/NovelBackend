# auth.py
from fastapi import Depends, HTTPException, status

def verify_token(token: str = "secret-token"):
    if token != "secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
