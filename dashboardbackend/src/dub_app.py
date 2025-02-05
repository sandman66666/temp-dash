"""
Main application factory for duplicated analytics dashboard
"""
import logging
import os
from quart import Quart
from quart_cors import cors
from dotenv import load_dotenv
from src.services.dub_analytics import AnalyticsService
from src.core import redis_client, opensearch_client

logger = logging.getLogger(__name__)

def create_app() -> Quart:
    """Create and configure the Quart application"""
    try:
        logger.info("Creating application...")
        
        # Load environment variables
        load_dotenv()
        
        # Create Quart app
        app = Quart(__name__)
        
        # Enable CORS
        app = cors(app, allow_origin="*")
        
        # Initialize analytics service
        logger.info("Initializing analytics service...")
        app.analytics_service = AnalyticsService(opensearch_client, redis_client)
        logger.info("Analytics service initialized")
        
        # Register blueprints
        logger.info("Registering blueprints...")
        from src.api.dub_metrics import metrics_bp
        
        # Register blueprints with explicit URL prefixes
        app.register_blueprint(metrics_bp, url_prefix='/dub_metrics')
        
        logger.info("Application created successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise

async def init_app() -> Quart:
    """Initialize the application"""
    app = create_app()
    return app