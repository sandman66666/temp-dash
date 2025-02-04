"""
Main application factory
"""
import logging
import os
from quart import Quart
from quart_cors import cors
from dotenv import load_dotenv
from src.core import init_services

logger = logging.getLogger(__name__)

def create_app() -> Quart:
    """Create and configure the Quart application"""
    try:
        logger.info("Registering application blueprints...")
        
        # Load environment variables
        load_dotenv()
        
        # Create Quart app
        app = Quart(__name__)
        
        # Enable CORS
        app = cors(app, allow_origin="*")
        
        # Register blueprints
        from src.api.metrics import metrics_bp
        from src.api.health import health_bp
        
        app.register_blueprint(metrics_bp, url_prefix='/metrics')
        app.register_blueprint(health_bp, url_prefix='/health')
        
        logger.info("Blueprints registered successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to register blueprints: {str(e)}")
        raise

async def init_app() -> Quart:
    """Initialize the application"""
    app = create_app()
    
    # Initialize services
    await init_services(app)
    
    return app