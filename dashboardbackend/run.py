"""
Run the application server
"""
import asyncio
import logging
import os
from hypercorn.config import Config
from hypercorn.asyncio import serve
from dotenv import load_dotenv
from src.app import init_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize application
app = None

async def init():
    global app
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize application
        app = await init_app()
        return app
    except Exception as e:
        logger.error(f"Failed to initialize app: {str(e)}")
        raise

async def main():
    """Main entry point"""
    try:
        app = await init()
        
        # Configure Hypercorn
        config = Config()
        config.bind = [f"0.0.0.0:{os.getenv('PORT', '5001')}"]
        config.use_reloader = True
        
        # Start server
        await serve(app, config)
        
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise

# Initialize app for Flask CLI
asyncio.run(init())

if __name__ == "__main__":
    asyncio.run(main())