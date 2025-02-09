from flask import Blueprint

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
async def health_check():
    """Health check endpoint."""
    return {'status': 'healthy'}, 200
