"""
Initialize application services and connections
"""
import logging
import os
from quart import Quart
from src.services.cache import cache
from opensearchpy import AsyncOpenSearch
import redis.asyncio as redis
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Redis client
redis_client = redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379'),
    decode_responses=True
)

# Initialize OpenSearch client
opensearch_client = AsyncOpenSearch(
    hosts=[os.getenv('OPENSEARCH_URL', 'https://localhost:9200')],
    http_auth=(
        os.getenv('OPENSEARCH_USERNAME', ''),
        os.getenv('OPENSEARCH_PASSWORD', '')
    ),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False
)

async def init_services(app: Quart) -> None:
    """Initialize all required services"""
    try:
        # Initialize Redis
        logger.info("Connecting to Redis...")
        await cache.connect()
        logger.info("Redis connection established")

        # Store cache instance in app context
        app.cache = cache

        # Add cleanup on app teardown
        @app.before_serving
        async def startup():
            logger.info("Starting up services...")

        @app.after_serving
        async def shutdown():
            logger.info("Shutting down services...")
            await cache.disconnect()
            await redis_client.close()
            await opensearch_client.close()

    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise

__all__ = ['redis_client', 'opensearch_client', 'init_services']