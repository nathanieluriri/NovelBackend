from core.redis_cache import cache_db
import random
from datetime import datetime
from services.email_service import send_email,send_warning_about_ip_change,send_change_of_password_otp_email
from repositories.admin_repo import get_location_details_for_admin,get_admin_by_email
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
    
    
def generate_otp_admin_password(email):
    otp_digit=""
    count=6
    min_val=0
    max_val=9
    otp=random.sample(range(min_val, max_val + 1), count)
    for digit in otp:
        otp_digit+=str(digit)
    cache_db.setex(name=otp_digit,value=email,time=380)
    return otp_digit


async def send_otp(otp:str,location:ClientData,user_email:str):
    old_location_data = await get_location_details_for_admin(user_id=location['userId'])
    if old_location_data:
        if old_location_data.ip==location['ip']:
            
            await send_email(location=location,receiver_email=user_email,otp=otp)
            return 0
        else:
            now = datetime.now()
            formatted = now.strftime("%A, %B %d, %Y at %I:%M %p")
            admin_data=await get_admin_by_email(email=user_email)
            await send_warning_about_ip_change(firstName=admin_data.firstName,lastName=admin_data.lastName,time_data=formatted,location=f"{location['city']}, {location['region']}, {location['country']} ",extra_data=f"Network-{location['Network'] }, Longitude: {location['longitude']}, latitude: {location['latitude']}" ,receiver_email=user_email,ip=location['ip'])
            await send_email(location=location,receiver_email=user_email,otp=otp)
    else:
        now = datetime.now()
        formatted = now.strftime("%A, %B %d, %Y at %I:%M %p")
        admin_data=await get_admin_by_email(email=user_email)
        await send_warning_about_ip_change(firstName=admin_data.firstName,lastName=admin_data.lastName,time_data=formatted,location=f"{location['city']}, {location['region']}, {location['country']} ",extra_data=f"Network-{location['Network'] } lon: {location['longitude']} ,lat: {location['latitude']}" ,receiver_email=user_email,ip=location['ip'])
        await send_email(location=location,receiver_email=user_email,otp=otp)
    
async def verify_otp(accessToken,otp):
    exists = cache_db.exists(accessToken)
    if exists:
        value = cache_db.get(accessToken)
        if value == otp:
            cache_db.delete(accessToken)
            decoded = await decode_jwt_token(accessToken)
            await update_admin_access_tokens(token=decoded['accessToken'])
            return True
        else: return False
        
        
        
        
async def send_otp_admin(otp:str,user_email:str):
    await send_change_of_password_otp_email(receiver_email=user_email,otp=otp)
    return 0
    
    
async def verify_otp_admin(email,otp):
    exists = cache_db.exists(otp)
    if exists:
        value = cache_db.get(otp)
        if value == email:
            cache_db.delete(otp)
            return True
        else: return False