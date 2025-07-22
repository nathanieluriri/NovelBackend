import redis

cache_db = redis.Redis(host="redis", port=6379)