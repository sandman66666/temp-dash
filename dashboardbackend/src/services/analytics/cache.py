"""
Redis cache service for analytics
"""
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache service"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return value.decode('utf-8')
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {str(e)}")
            return None

    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in cache with optional expiration"""
        if not self.redis:
            return False

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)

            if expire:
                await self.redis.setex(key, expire, value)
            else:
                await self.redis.set(key, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set failed: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete failed: {str(e)}")
            return False