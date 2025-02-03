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
import aiohttp
import ssl
import certifi

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

async def fetch_descope_users(trace_ids: list[str]) -> list[dict]:
    """Fetch user details from Descope for given trace_ids (v2UserIds)"""
    descope_url = os.getenv('DESCOPE_API_URL', 'https://api.descope.com/v1/mgmt/user/search')
    bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
    
    if not bearer_token:
        logger.error("Descope bearer token not found in environment variables")
        return []
        
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    
    # Search for users with matching v2UserId custom attribute
    payload = {
        "customAttributes": {
            "v2UserId": trace_ids  # Descope will match any v2UserId in this list
        }
    }
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        conn = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.post(descope_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    users = data.get('users', [])
                    
                    # Map users to include both email and trace_id (v2UserId)
                    user_details = []
                    for user in users:
                        v2user_id = user.get('customAttributes', {}).get('v2UserId')
                        if v2user_id and v2user_id in trace_ids:  # Only include users whose v2UserId matches our trace_ids
                            user_details.append({
                                'email': user.get('email', ''),
                                'trace_id': v2user_id
                            })
                    return user_details
                else:
                    error_text = await response.text()
                    logger.error("Descope API error: %s - %s", response.status, error_text)
                    return []
    except Exception as e:
        logger.error("Error fetching Descope users: %s", str(e))
        return []

@metrics_bp.route('/metrics/gauge-users')
async def get_gauge_user_candidates():
    """Get the list of users based on gauge type with their emails"""
    try:
        # Parse startDate and endDate from query parameters
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        gauge_type = request.args.get('gaugeType', 'thread_users')  # Default to thread_users if not specified
        
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
        
        # Create analytics service instance
        analytics_service = AnalyticsService(
            opensearch_client=opensearch_client,
            redis_client=current_app.cache.redis
        )

        # Build query based on gauge type
        time_filter = {
            "range": {
                "timestamp": {
                    "gte": analytics_service._format_date_os(start_date),
                    "lte": analytics_service._format_date_os(end_date)
                }
            }
        }

        # Configure query based on gauge type
        event_name = "handleMessageInThread_start"
        count_condition = "params.count >= 1"  # Default for thread_users

        if gauge_type == "sketch_users":
            event_name = "uploadSketch_end"
            count_condition = "params.count >= 1"
        elif gauge_type == "render_users":
            event_name = "renderStart_end"
            count_condition = "params.count >= 1"
        elif gauge_type == "medium_chat_users":
            event_name = "handleMessageInThread_start"
            count_condition = "params.count >= 5 && params.count <= 20"
        elif gauge_type == "active_chat_users":
            event_name = "handleMessageInThread_start"
            count_condition = "params.count > 20"

        query = analytics_service.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": event_name}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "thread_count": {
                        "terms": {"field": "trace_id.keyword", "size": 10000},
                        "aggs": {
                            "thread_filter": {
                                "bucket_selector": {
                                    "buckets_path": {"count": "_count"},
                                    "script": count_condition
                                }
                            }
                        }
                    }
                }
            }
        )

        result = await opensearch_client.search(
            index=analytics_service.index,
            body=query,
            size=0
        )

        # Extract the trace_ids from the buckets
        trace_ids = [
            bucket["key"]
            for bucket in result["aggregations"]["thread_count"]["buckets"]
        ]

        # Fetch user details from Descope for these trace_ids
        user_details = await fetch_descope_users(trace_ids)

        return {
            "status": "success",
            "data": user_details,  # List of dicts with email and trace_id
            "timeRange": {
                "start": analytics_service._format_date_iso(start_date),
                "end": analytics_service._format_date_iso(end_date)
            }
        }

    except Exception as e:
        logger.error("Error fetching gauge user candidates: %s", str(e), exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timeRange": {
                "start": start_date.isoformat() + "Z",
                "end": end_date.isoformat() + "Z"
            }
        }, 500

def init_app(app):
    """Register blueprint with app"""
    app.register_blueprint(metrics_bp)