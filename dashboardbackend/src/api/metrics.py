"""
Metrics API endpoints
"""
from datetime import datetime, timezone
from typing import Optional
from quart import Blueprint, jsonify, request, current_app
from src.services.analytics_service import AnalyticsService
from src.core import redis_client, opensearch_client

metrics_bp = Blueprint('metrics', __name__)
analytics_service = AnalyticsService(opensearch_client, redis_client)

def init_app(app):
    """Initialize metrics blueprint"""
    app.register_blueprint(metrics_bp, url_prefix='/metrics')

@metrics_bp.route('/', methods=['GET'])
async def get_metrics():
    """Get dashboard metrics"""
    try:
        # Parse date parameters
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        include_v1 = request.args.get('includeV1', 'true').lower() == 'true'

        current_app.logger.info(f"Fetching metrics with params: start={start_date}, end={end_date}, include_v1={include_v1}")

        if not start_date or not end_date:
            current_app.logger.error("Missing date parameters")
            return jsonify({
                'error': 'Missing date parameters'
            }), 400

        try:
            # Convert to datetime objects
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError as e:
            current_app.logger.error(f"Invalid date format: {str(e)}")
            return jsonify({
                'error': 'Invalid date format'
            }), 400

        # Get metrics with V1 data
        metrics_data = await analytics_service.get_dashboard_metrics(
            start_date=start_date,
            end_date=end_date,
            include_v1=include_v1
        )

        current_app.logger.info(f"Successfully fetched metrics: {metrics_data}")
        return jsonify(metrics_data)

    except Exception as e:
        current_app.logger.error(f"Error in get_metrics: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500

@metrics_bp.route('/user-stats', methods=['GET'])
async def get_user_stats():
    """Get user statistics"""
    try:
        # Parse parameters
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        gauge_type = request.args.get('gaugeType')

        current_app.logger.info(f"Fetching user stats with params: start={start_date}, end={end_date}, gauge_type={gauge_type}")

        if not all([start_date, end_date, gauge_type]):
            current_app.logger.error("Missing required parameters")
            return jsonify({
                'error': 'Missing required parameters'
            }), 400

        try:
            # Convert to datetime objects
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError as e:
            current_app.logger.error(f"Invalid date format: {str(e)}")
            return jsonify({
                'error': 'Invalid date format'
            }), 400

        # Get user statistics
        user_stats = await analytics_service.get_user_statistics(
            start_date=start_date,
            end_date=end_date,
            gauge_type=gauge_type
        )

        current_app.logger.info(f"Successfully fetched user stats: {len(user_stats)} users")
        return jsonify({
            'status': 'success',
            'data': user_stats,
            'timeRange': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error in get_user_stats: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500

@metrics_bp.route('/user-events', methods=['GET'])
async def get_user_events():
    """Get user events"""
    try:
        # Parse parameters
        trace_id = request.args.get('traceId')
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')

        current_app.logger.info(f"Fetching user events: traceId={trace_id}, start={start_date}, end={end_date}")

        if not all([trace_id, start_date, end_date]):
            current_app.logger.error("Missing required parameters")
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameters'
            }), 400

        try:
            # Convert dates with UTC timezone
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

            # Ensure dates are in UTC
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            # Get user events
            events = await analytics_service.get_user_events(
                trace_id=trace_id,
                start_date=start_date,
                end_date=end_date
            )

            return jsonify({
                'status': 'success',
                'data': events,
                'timeRange': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            })

        except ValueError as e:
            current_app.logger.error(f"Date format error: {e}")
            return jsonify({
                'status': 'error',
                'error': f'Invalid date format: {str(e)}'
            }), 400

    except Exception as e:
        current_app.logger.error(f"Error in get_user_events: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500