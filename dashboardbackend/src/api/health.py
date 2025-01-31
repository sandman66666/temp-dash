"""
Health check and monitoring endpoints
"""
from quart import Blueprint, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
async def health_check():
    """Check health of all services"""
    try:
        # Test Redis connection
        cache_stats = await current_app.cache.get_cache_stats()
        
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'redis': {
                    'status': 'connected',
                    'stats': cache_stats
                }
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }, 500

def init_app(app):
    """Register blueprint with app"""
    app.register_blueprint(health_bp)