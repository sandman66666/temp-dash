"""
Health check endpoints
"""
from quart import Blueprint, jsonify
from src.core import redis_client, opensearch_client

health_bp = Blueprint('health', __name__)

def init_app(app):
    """Initialize health blueprint"""
    app.register_blueprint(health_bp, url_prefix='/health')

@health_bp.route('/', methods=['GET'])
async def health_check():
    """Basic health check endpoint"""
    try:
        # Check Redis connection
        redis_status = "healthy"
        try:
            await redis_client.ping()
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"

        # Check OpenSearch connection
        opensearch_status = "healthy"
        try:
            await opensearch_client.ping()
        except Exception as e:
            opensearch_status = f"unhealthy: {str(e)}"

        return jsonify({
            'status': 'ok',
            'services': {
                'redis': redis_status,
                'opensearch': opensearch_status
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500