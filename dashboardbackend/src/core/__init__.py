"""
Initialize application services and connections
"""
import logging
from quart import Quart
from src.services.cache import cache
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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

    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise