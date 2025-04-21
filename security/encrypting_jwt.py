import jwt
import datetime
from datetime import timezone
from core.database import db
from dotenv import load_dotenv
import os
import asyncio
from bson import ObjectId

load_dotenv()
SECRETID = os.getenv("SECRETID")


async def get_secret_dict()->dict:
    result =await db.secret_keys.find_one({"_id":ObjectId(SECRETID)})
    result.pop('_id')
    return result



async def get_secret_and_header():
    
    import random
    
    secrets = await get_secret_dict()
    
    random_key = random.choice(list(secrets.keys()))
    random_secret = secrets[random_key]
    SECRET_KEYS={random_key:random_secret}
    HEADERS = {"kid":random_key}
    result = {
        "SECRET_KEY":SECRET_KEYS,
        "HEADERS":HEADERS
    }
    
    return result



async def create_jwt_member_token(token):
    secrets = await get_secret_and_header()
    SECRET_KEYS= secrets['SECRET_KEY']
    headers= secrets['HEADERS']
    
    payload = {
        'accessToken': token,
        'role':'member',
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=20)
    }

    
    token = jwt.encode(payload, SECRET_KEYS[headers['kid']], algorithm='HS256', headers=headers)

    print(token)
    return token

async def create_jwt_admin_token(token):
    secrets = await get_secret_and_header()
    SECRET_KEYS= secrets['SECRET_KEY']
    headers= secrets['HEADERS']
    
    payload = {
        'accessToken': token,
        'role':'admin',
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=20)
    }

    
    token = jwt.encode(payload, SECRET_KEYS[headers['kid']], algorithm='HS256', headers=headers)

    print(token)
    return token



async def decode_jwt_token(token):
    SECRET_KEYS = await get_secret_dict()
    # Decode header to extract the `kid`
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header['kid']

    # Look up the correct key
    key = SECRET_KEYS.get(kid)

    if not key:
        raise Exception("Unknown key ID")

    # Now decode and verify
    try:
        decoded = jwt.decode(token, key, algorithms=['HS256'])
        print(decoded)
        return decoded
    except jwt.exceptions.ExpiredSignatureError:
        print("expired token")
        return None





