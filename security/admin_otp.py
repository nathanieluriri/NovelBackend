from core.redis_cache import cache_db
from random import random

def generate_otp(admin_access_token):
    count=6
    min_val=1
    max_val=49
    otp=random.sample(range(min_val, max_val + 1), count)
    cache_db.setex(name=admin_access_token,value=otp,time=380)
    return otp
    
    # TODO: write function for sending otp
def send_otp(otp):
    pass