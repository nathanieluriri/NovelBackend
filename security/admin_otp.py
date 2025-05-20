from core.redis_cache import cache_db
import random
from services.email_service import send_email
from schemas.email_schema import ClientData
from security.encrypting_jwt import decode_jwt_token
from repositories.tokens_repo import update_admin_access_tokens
def generate_otp(admin_access_token):
    otp_digit=""
    count=6
    min_val=0
    max_val=9
    otp=random.sample(range(min_val, max_val + 1), count)
    for digit in otp:
        otp_digit+=str(digit)
    cache_db.setex(name=admin_access_token,value=otp_digit,time=380)
    return otp_digit
    
    # TODO: write function for sending otp
async def send_otp(otp:str,location:ClientData,user_email:str):
    await send_email(location=location,receiver_email=user_email,otp=otp)
    
    
    
async def verify_otp(accessToken,otp):
    exists = cache_db.exists(accessToken)
    if exists:
        value = cache_db.get(accessToken)
        if value == otp:
            decoded = await decode_jwt_token(accessToken)
            await update_admin_access_tokens(token=decoded['accessToken'])
            return True
        else: return False