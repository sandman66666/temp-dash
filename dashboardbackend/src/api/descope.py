# dashboardbackend/src/api/descope.py
from quart import Blueprint, jsonify
import os
import logging
import aiohttp
import ssl

logger = logging.getLogger(__name__)
descope_bp = Blueprint('descope', __name__)

@descope_bp.route('/getDescopeUsers', methods=['GET'])
async def get_descope_users():
    """
    Retrieves users from the Descope API.
    Expects DESCOPE_API_URL and DESCOPE_BEARER_TOKEN to be set in your environment.
    """
    descope_url = os.getenv('DESCOPE_API_URL')
    bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
    
    if not descope_url or not bearer_token:
        logger.error("Descope configuration missing.")
        return jsonify({"error": "Descope configuration missing"}), 500

    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        "tenantIds": [],
        "text": "",
        "roleNames": [],
        "loginIds": [],
        "ssoAppIds": [],
        "customAttributes": {}
    }

    # For development only: create an SSL context that disables certificate verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(descope_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    users = data.get('users', [])
                    return jsonify({"users": users})
                else:
                    error_text = await response.text()
                    logger.error(f"Descope API error: {response.status}: {error_text}")
                    return jsonify({"error": f"Descope API error: {response.status}", "details": error_text}), response.status
    except Exception as e:
        logger.error(f"Error fetching Descope users: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def init_app(app):
    """Register the Descope blueprint with the Quart app."""
    app.register_blueprint(descope_bp)