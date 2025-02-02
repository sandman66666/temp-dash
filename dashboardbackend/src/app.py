"""
Main application entry point
"""
from quart import Quart
from quart_cors import cors
import logging
from dotenv import load_dotenv
from src.core import init_services
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def create_app():
    """Create and configure application"""
    app = Quart(__name__)
    
    # Configure CORS
    app = cors(
        app, 
        allow_origin=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_headers=["Content-Type"],
        allow_methods=["GET", "POST", "OPTIONS"]
    )
    
    logger.info("Registering application blueprints...")
    try:
        from src.api.health import init_app as init_health
        from src.api.metrics import init_app as init_metrics
        from src.api.tasks import init_app as init_tasks
        from src.api.descope import init_app as init_descope
        
        init_health(app)
        init_metrics(app)
        init_tasks(app)
        init_descope(app)
        
        logger.info("Blueprints registered successfully")
    except Exception as e:
        logger.error(f"Failed to register blueprints: {str(e)}")
        raise

    return app

async def init_app():
    """Initialize application and all services"""
    app = create_app()
    await init_services(app)
    return app