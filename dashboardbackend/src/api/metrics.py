"""
Metrics API endpoints
"""
from quart import Blueprint, current_app
import logging
from datetime import datetime
from src.services.analytics_service import AnalyticsService
from opensearchpy import AsyncOpenSearch
import os

logger = logging.getLogger(__name__)
metrics_bp = Blueprint('metrics', __name__)

@metrics_bp.route('/metrics')
async def get_metrics():
    """Get all dashboard metrics"""
    try:
        # Initialize OpenSearch client
        opensearch_client = AsyncOpenSearch(
            hosts=[os.getenv('OPENSEARCH_URL', 'https://localhost:9200')],
            http_auth=(
                os.getenv('OPENSEARCH_USERNAME', 'elkadmin'),
                os.getenv('OPENSEARCH_PASSWORD', '')
            ),
            verify_certs=False  # For development only
        )
        
        # Create analytics service instance
        analytics_service = AnalyticsService(
            opensearch_client=opensearch_client,
            redis_client=current_app.cache.redis
        )
        
        # Fetch metrics
        metrics = await analytics_service.get_dashboard_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }, 500

def init_app(app):
    """Register blueprint with app"""
    app.register_blueprint(metrics_bp)