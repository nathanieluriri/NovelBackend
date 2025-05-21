from core.redis_cache import cache_db
import random
from datetime import datetime
from services.email_service import send_change_of_password_otp_email
from security.encrypting_jwt import decode_jwt_token

def generate_otp(email):
    otp_digit=""
    count=6
    min_val=0
    max_val=9
    otp=random.sample(range(min_val, max_val + 1), count)
    for digit in otp:
        otp_digit+=str(digit)
    cache_db.setex(name=otp_digit,value=email,time=380)
    return otp_digit
    
async def send_otp_user(otp:str,user_email:str):
    await send_change_of_password_otp_email(receiver_email=user_email,otp=otp)
    return 0
    
    
async def verify_otp(email,otp):
    exists = cache_db.exists(otp)
    if exists:
        value = cache_db.get(otp)
        if value == email:
            cache_db.delete(otp)
            return True
        else: return False