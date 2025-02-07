"""
Descope service for user management and authentication
"""
import logging
from typing import Dict, List, Optional
import os
import aiohttp
import certifi
import ssl
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

class DescopeService:
    """Service for interacting with Descope API"""

    def __init__(self):
        """Initialize Descope service"""
        self.api_url = os.getenv('DESCOPE_API_URL', 'https://api.descope.com/v1/mgmt/user/search')
        self.bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
        
        # Configure SSL context
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        if not self.bearer_token:
            logger.warning("Missing Descope bearer token. Some features may be limited.")
        else:
            logger.info("Successfully initialized Descope service with bearer token")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def get_total_users(self, date: Optional[datetime] = None) -> int:
        """Get total number of users from Descope.
        
        Args:
            date: Optional datetime to filter users by registration date
            
        Returns:
            int: Total number of users
            
        Raises:
            Exception: If there's an error fetching users from Descope
        """
        try:
            if not self.bearer_token:
                logger.warning("Missing Descope bearer token, returning 0 users")
                return 0

            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }

            total_users = 0
            page_size = 100
            has_more = True
            page_number = 1

            while has_more:
                # Use empty filters to get all users with pagination
                body = {
                    "tenantIds": [],
                    "roleNames": [],
                    "customAttributes": {},
                    "limit": page_size,
                    "page": page_number
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(self.api_url, headers=headers, json=body, ssl=self.ssl_context) as response:
                        if response.status == 200:
                            data = await response.json()
                            users = data.get('users', [])
                            total_users += len(users)
                            
                            # Check if we have more pages
                            if len(users) < page_size:
                                has_more = False
                            else:
                                page_number += 1
                                logger.debug(f"Fetching page {page_number} of users")
                        else:
                            error_text = await response.text()
                            logger.error(f"Failed to get users from Descope. Status: {response.status}, Error: {error_text}")
                            return 0

            logger.info(f"Successfully fetched total users from Descope: {total_users}")
            return total_users

        except Exception as e:
            logger.error(f"Error getting total users from Descope: {str(e)}", exc_info=True)
            return 0

    async def get_active_users(self, start_date: datetime, end_date: datetime) -> int:
        """Get number of active users in date range"""
        if not self.bearer_token:
            logger.error("Missing Descope credentials")
            return 0

        try:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }
            
            query = {
                "pageSize": 1,
                "page": 1,
                "loginTime": {
                    "after": start_date.isoformat(),
                    "before": end_date.isoformat()
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/activity", headers=headers, json=query, ssl=self.ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        active = data.get('totalUsers', 0)
                        logger.info(f"Successfully fetched active users from Descope: {active}")
                        return active
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get active users from Descope. Status: {response.status}, Error: {error_text}")
                        return 0

        except Exception as e:
            logger.error(f"Error getting active users from Descope: {str(e)}")
            return 0

    async def get_user_details(self, user_ids: List[str]) -> Dict[str, Dict]:
        """Get user details from Descope.
        
        Args:
            user_ids: List of user IDs to fetch details for
            
        Returns:
            Dict[str, Dict]: Dictionary mapping user IDs to their details
            
        Raises:
            Exception: If there's an error fetching user details from Descope
        """
        try:
            if not self.bearer_token:
                logger.warning("Missing Descope bearer token, returning empty user details")
                return {}

            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }

            # Search for specific users by their IDs
            body = {
                "tenantIds": [],
                "roleNames": [],
                "customAttributes": {},
                "loginIds": user_ids,
                "limit": len(user_ids)
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=body, ssl=self.ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('users', [])
                        # Map user details by their ID
                        user_details = {user.get('loginIds', [''])[0]: user for user in users}
                        logger.info(f"Successfully fetched details for {len(user_details)} users")
                        return user_details
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get user details from Descope. Status: {response.status}, Error: {error_text}")
                        return {}

        except Exception as e:
            logger.error(f"Error getting user details from Descope: {str(e)}", exc_info=True)
            return {}