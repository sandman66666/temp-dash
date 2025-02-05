"""
Descope API service for user management and authentication
"""
import os
import logging
import ssl
import aiohttp
import certifi
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DescopeService:
    """Handles all Descope API interactions"""

    def __init__(self):
        self.api_url = os.getenv('DESCOPE_API_URL', 'https://api.descope.com/v1/mgmt/user/search')
        self.bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
        
        # Configure SSL context
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        # Flag to track if we're using mock data
        self.use_mock_data = False

    async def get_total_users(self, end_date: Optional[datetime] = None, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get total users count within date range"""
        if not self.bearer_token:
            logger.error("No Descope bearer token provided")
            return {
                "value": 0,
                "previousValue": 0,
                "trend": "neutral",
                "changePercentage": 0,
                "daily_average": 0
            }

        try:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
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

            if end_date:
                payload["endTime"] = end_date.isoformat()
            if start_date:
                payload["startTime"] = start_date.isoformat()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    ssl=self.ssl_context
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('users', [])
                        total_value = len(users)
                        logger.info(f"Found {total_value} users in Descope")

                        # Calculate metrics
                        days_in_range = (end_date - start_date).days + 1 if start_date and end_date else 1
                        daily_average = total_value / days_in_range if days_in_range > 0 else 0

                        return {
                            "value": total_value,
                            "previousValue": 0,  # We don't have historical data
                            "trend": "up" if total_value > 0 else "neutral",
                            "changePercentage": 0,  # No historical comparison
                            "daily_average": daily_average
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Descope API error: {response.status} - {error_text}")
                        return {
                            "value": 0,
                            "previousValue": 0,
                            "trend": "neutral",
                            "changePercentage": 0,
                            "daily_average": 0
                        }

        except Exception as e:
            logger.error(f"Error fetching total users from Descope: {str(e)}", exc_info=True)
            return {
                "value": 0,
                "previousValue": 0,
                "trend": "neutral",
                "changePercentage": 0,
                "daily_average": 0
            }

    async def get_user_details(self, user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get user details from Descope"""
        if not self.bearer_token:
            logger.error("No Descope bearer token provided")
            return {}

        if not user_ids:
            logger.warning("No user IDs provided")
            return {}

        try:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }

            # Split user IDs into chunks to avoid too large requests
            chunk_size = 100
            user_details = {}

            for i in range(0, len(user_ids), chunk_size):
                chunk = user_ids[i:i + chunk_size]
                
                payload = {
                    "tenantIds": [],
                    "text": "",
                    "roleNames": [],
                    "loginIds": chunk,
                    "ssoAppIds": [],
                    "customAttributes": {}
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        ssl=self.ssl_context
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            users = data.get('users', [])
                            logger.info(f"Found {len(users)} users in Descope for chunk of {len(chunk)} IDs")
                            
                            # Create mapping of loginId to user details
                            for user in users:
                                login_id = user.get('loginId')
                                if login_id and login_id in chunk:
                                    user_details[login_id] = {
                                        'email': user.get('email', ''),
                                        'v2UserId': user.get('userId', ''),  # Changed to userId
                                        'createdTime': user.get('createdTime', ''),
                                        'lastLoginTime': user.get('lastLoginTime', '')
                                    }
                        else:
                            error_text = await response.text()
                            logger.error(f"Descope API error: {response.status} - {error_text}")

            # For any user IDs that weren't found, add placeholder data
            for user_id in user_ids:
                if user_id not in user_details:
                    user_details[user_id] = {
                        'email': f'Unknown ({user_id})',
                        'v2UserId': user_id,  # Use the trace_id as v2UserId for unknown users
                        'createdTime': '',
                        'lastLoginTime': ''
                    }

            return user_details

        except Exception as e:
            logger.error(f"Error fetching user details from Descope: {str(e)}", exc_info=True)
            return {user_id: {
                'email': f'Error ({user_id})',
                'v2UserId': user_id,  # Use the trace_id as v2UserId for error cases
                'createdTime': '',
                'lastLoginTime': ''
            } for user_id in user_ids}