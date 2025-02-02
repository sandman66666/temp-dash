"""
Metrics API endpoints
"""
from quart import Blueprint, current_app, request
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse
from src.services.analytics_service import AnalyticsService
from opensearchpy import AsyncOpenSearch
import os

logger = logging.getLogger(__name__)
metrics_bp = Blueprint('metrics', __name__)

@metrics_bp.route('/metrics')
async def get_metrics():
    """Get all dashboard metrics with time filtering"""
    try:
        # Parse startDate and endDate from query parameters
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        if start_date_str and end_date_str:
            start_date = parse(start_date_str)
            end_date = parse(end_date_str)
            logger.debug("Parsed query dates - start_date: %s, end_date: %s", start_date, end_date)
        else:
            # Default to last 7 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            logger.debug("No query dates provided. Using default - start_date: %s, end_date: %s", start_date, end_date)
        
        # Initialize OpenSearch client
        opensearch_url = os.getenv('OPENSEARCH_URL', 'https://localhost:9200')
        opensearch_client = AsyncOpenSearch(
            hosts=[opensearch_url],
            http_auth=(
                os.getenv('OPENSEARCH_USERNAME', 'elkadmin'),
                os.getenv('OPENSEARCH_PASSWORD', '')
            ),
            verify_certs=False  # For development only; update in production!
        )
        logger.debug("Initialized OpenSearch client with host: %s", opensearch_url)
        
        # Create analytics service instance
        analytics_service = AnalyticsService(
            opensearch_client=opensearch_client,
            redis_client=current_app.cache.redis
        )
        logger.debug("AnalyticsService instance created.")
        
        # Fetch metrics with time filtering
        metrics = await analytics_service.get_dashboard_metrics(start_date, end_date)
        logger.debug("Fetched metrics: %s", metrics)
        return metrics
        
    except Exception as e:
        logger.error("Error fetching metrics: %s", str(e), exc_info=True)
        # Even in error cases, return a timeRange property so the frontend doesn't crash.
        default_end = datetime.utcnow()
        default_start = default_end - timedelta(days=7)
        error_response = {
            'status': 'error',
            'error': str(e),
            'timeRange': {
                'start': default_start.isoformat() + "Z",
                'end': default_end.isoformat() + "Z"
            }
        }
        logger.debug("Returning error response: %s", error_response)
        return error_response, 500

def init_app(app):
    """Register blueprint with app"""
    app.register_blueprint(metrics_bp)