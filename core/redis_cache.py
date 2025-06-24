import redis

cache_db = redis.Redis(
    host="localhost",  # Local Redis on EC2 host
    port=6379,
    decode_responses=True
)