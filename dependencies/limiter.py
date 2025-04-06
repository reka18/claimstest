import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from config import REDIS_URL

async def init_limiter():
    redis_instance = redis.from_url(REDIS_URL, decode_responses=True)
    await FastAPILimiter.init(redis_instance)