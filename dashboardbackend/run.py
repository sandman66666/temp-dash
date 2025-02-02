"""
Main entry point for running the backend server
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root directory to Python path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from src.app import init_app
import hypercorn.asyncio
from hypercorn.config import Config

# Configure logging to output debug information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    app = await init_app()
    config = Config()
    port = os.getenv('PORT', '5001')
    config.bind = [f"localhost:{port}"]
    config.use_reloader = True
    
    logger.info("Starting Dashboard Backend server...")
    logger.info(f"Server running on http://localhost:{port}")
    logger.info("Press CTRL+C to quit")
    
    await hypercorn.asyncio.serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())