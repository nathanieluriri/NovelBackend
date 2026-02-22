import redis
import os

cache_db = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    username=os.getenv("REDIS_USERNAME") or None,
    password=os.getenv("REDIS_PASSWORD") or None,
    decode_responses=True
)