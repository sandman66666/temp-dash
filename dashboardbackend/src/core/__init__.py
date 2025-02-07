"""
Initialize application services and connections
"""
import logging
import os
from quart import Quart
from src.services.caching_service import CachingService
from src.services.analytics_service import AnalyticsService
from src.services.descope_service import DescopeService
from src.services.opensearch_service import OpenSearchService
from src.utils.query_builder import OpenSearchQueryBuilder
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
        # Initialize CachingService
        caching_service = CachingService(redis_client)

        # Store cache instance in app context
        app.cache = caching_service

        # Initialize OpenSearchQueryBuilder
        query_builder = OpenSearchQueryBuilder()

        # Initialize OpenSearchService
        opensearch_service = OpenSearchService()
        
        # Verify OpenSearch connection
        connection_verified = await opensearch_service.verify_connection()
        if not connection_verified:
            logger.error("Failed to verify OpenSearch connection. Analytics functionality may be limited.")
        else:
            logger.info("OpenSearch connection verified successfully")

        # Initialize DescopeService
        descope_service = DescopeService()

        # Initialize AnalyticsService
        analytics_service = AnalyticsService(
            caching_service,
            opensearch_service,
            query_builder,
            descope_service
        )

        # Store services in app context
        app.cache = caching_service
        app.descope_service = descope_service
        app.analytics_service = analytics_service
        app.opensearch_service = opensearch_service

        # Add cleanup on app teardown
        @app.before_serving
        async def startup():
            logger.info("Starting up services...")

        @app.after_serving
        async def shutdown():
            logger.info("Shutting down services...")
            await caching_service.disconnect()
            await redis_client.close()
            await opensearch_service.client.close()

    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise

__all__ = ['redis_client', 'opensearch_client', 'init_services']