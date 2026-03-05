from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from backend.app.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


def get_redis_client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()
