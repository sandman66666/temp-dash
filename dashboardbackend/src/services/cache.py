"""
Redis cache implementation for analytics data using redis-py
"""
import redis.asyncio as redis
import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis: Optional[redis.Redis] = None
        self._default_ttl = timedelta(minutes=5)

    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

    async def set_data(self, 
                      key: str, 
                      data: Any, 
                      ttl: Optional[timedelta] = None) -> bool:
        """
        Set data in Redis cache with optional TTL
        
        Args:
            key: Cache key
            data: Data to cache (will be JSON serialized)
            ttl: Optional time-to-live (defaults to 5 minutes)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.redis:
            logger.error("Redis not connected")
            return False

        try:
            # Convert data to JSON string
            json_data = json.dumps(data)
            
            # Use provided TTL or default
            expiry = ttl or self._default_ttl
            
            # Set with expiry
            await self.redis.set(
                key,
                json_data,
                ex=int(expiry.total_seconds())
            )
            
            logger.debug(f"Successfully cached data for key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching data for key {key}: {str(e)}")
            return False

    async def get_data(self, key: str) -> Optional[Any]:
        """
        Get data from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached data if exists, None otherwise
        """
        if not self.redis:
            logger.error("Redis not connected")
            return None

        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached data for key {key}: {str(e)}")
            return None

    async def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache key
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.redis:
            logger.error("Redis not connected")
            return False

        try:
            await self.redis.delete(key)
            logger.debug(f"Invalidated cache for key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache for key {key}: {str(e)}")
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
            
            return {
                "total_keys": len(keys),
                "used_memory": info.get('used_memory_human'),
                "connected_clients": info.get('connected_clients'),
                "last_save_time": datetime.fromtimestamp(
                    int(info.get('rdb_last_save_time', 0))
                ).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}

# Create a singleton instance
cache = RedisCache()