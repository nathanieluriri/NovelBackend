
import redis
import os
from dotenv import load_dotenv


load_dotenv()
REDIS_HOST=os.getenv('REDIS_HOST')
REDIS_PORT=os.getenv('REDIS_PORT')
REDIS_USERNAME=os.getenv('REDIS_USERNAME')
REDIS_PASSWORD=os.getenv('REDIS_PASSWORD')

cache_db = redis.Redis(
    host=REDIS_HOST,
    port=   int(REDIS_PORT),
    decode_responses=True,
    username=REDIS_USERNAME,
    password=REDIS_PASSWORD,
)

