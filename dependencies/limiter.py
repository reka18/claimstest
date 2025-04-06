import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from config import REDIS_URL

async def init_limiter():
    """
    Initialize the FastAPI rate limiter using a Redis backend.

    This function sets up FastAPILimiter with a Redis instance for distributed,
    asynchronous rate limiting across API endpoints. It should be called during
    FastAPI application startup.

    The Redis instance is created using the configured REDIS_URL and is shared
    by FastAPILimiter to track request counts per user/IP.

    Raises:
        redis.exceptions.ConnectionError: If Redis is unreachable or misconfigured.
    """
    redis_instance = redis.from_url(REDIS_URL, decode_responses=True)
    await FastAPILimiter.init(redis_instance)