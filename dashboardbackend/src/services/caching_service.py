"""
Caching service for storing and retrieving cached data
"""
import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class CachingService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = timedelta(minutes=5)

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Successfully retrieved cached data for key: {key}")
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set value in cache with optional expiration"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)

            expiry = ttl or self.default_ttl
            await self.redis.set(key, value, ex=int(expiry.total_seconds()))
            logger.debug(f"Successfully cached data for key: {key}")
            return True
        except Exception as e:
            logger.warning(f"Redis set failed: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            await self.redis.delete(key)
            logger.debug(f"Successfully deleted cached data for key: {key}")
            return True
        except Exception as e:
            logger.warning(f"Redis delete failed: {str(e)}")
            return False

    async def clear_all(self) -> bool:
        """Clear all cached data"""
        try:
            await self.redis.flushdb()
            logger.info("Successfully cleared all cached data")
            return True
        except Exception as e:
            logger.warning(f"Redis flush failed: {str(e)}")
            return False

    async def get_or_set(self, key: str, value_func, ttl: Optional[timedelta] = None) -> Any:
        """Get value from cache or set it if not present"""
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        value = await value_func()
        await self.set(key, value, ttl)
        return value

    async def get_many(self, keys: list) -> dict:
        """Get multiple values from cache"""
        try:
            values = await self.redis.mget(keys)
            result = {key: json.loads(value) if value else None for key, value in zip(keys, values)}
            logger.debug(f"Successfully retrieved multiple cached data for keys: {keys}")
            return result
        except Exception as e:
            logger.warning(f"Redis mget failed: {str(e)}")
            return {key: None for key in keys}

    async def set_many(self, data: dict, ttl: Optional[timedelta] = None) -> bool:
        """Set multiple values in cache with optional expiration"""
        try:
            pipeline = self.redis.pipeline()
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                elif not isinstance(value, str):
                    value = str(value)
                
                expiry = ttl or self.default_ttl
                pipeline.set(key, value, ex=int(expiry.total_seconds()))
            
            await pipeline.execute()
            logger.debug(f"Successfully cached multiple data for keys: {list(data.keys())}")
            return True
        except Exception as e:
            logger.warning(f"Redis mset failed: {str(e)}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict with cache stats
        """
        if not self.redis:
            logger.error("Redis not connected")
            return {}

        try:
            info = await self.redis.info()
            keys = await self.redis.keys('*')
            
            stats = {
                "total_keys": len(keys),
                "used_memory": info.get('used_memory_human'),
                "connected_clients": info.get('connected_clients'),
                "last_save_time": datetime.fromtimestamp(
                    int(info.get('rdb_last_save_time', 0))
                ).isoformat()
            }
            logger.debug("Successfully retrieved cache stats")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}