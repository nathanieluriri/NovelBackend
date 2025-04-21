from core.database import db
from schemas.tokens_schema import accessTokenCreate,refreshTokenCreate,accessTokenOut,refreshTokenOut
import asyncio
from bson import ObjectId,errors

async def add_access_tokens(token_data:accessTokenCreate)->accessTokenOut:
    token = token_data.model_dump()
    result = await db.accessToken.insert_one(token)
    tokn = await db.accessToken.find_one({"_id":result.inserted_id})
    accessToken = accessTokenOut(**tokn)
    
    return accessToken 
    

async def add_refresh_tokens(token_data:refreshTokenCreate)->refreshTokenOut:
    token = token_data.model_dump()
    result = await db.refreshToken.insert_one(token)
    tokn = await db.refreshToken.find_one({"_id":result.inserted_id})
    refreshToken = refreshTokenOut(**tokn)
    return refreshToken


async def get_access_tokens(accessToken:str):
    
    token = await db.accessToken.find_one({"_id": ObjectId(accessToken)})
    if token:
        tokn = accessTokenOut(**token)
        return tokn
    else:
        print("No token found")
        return None
async def get_refresh_tokens(refreshToken:str):
    token = await db.refreshToken.find_one({"_id": ObjectId(refreshToken)})
    if token:
        tokn = refreshTokenOut(**token)
        return tokn

    else: return None

