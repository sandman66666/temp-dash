"""
Descope service for user management and authentication
"""
import logging
from typing import Dict, List, Optional, Any
import os
import aiohttp
import certifi
import ssl
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed, wait_exponential

logger = logging.getLogger(__name__)

class DescopeService:
    """Service for interacting with Descope API"""

    def __init__(self):
        """Initialize Descope service"""
        self.bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
        
        if not self.bearer_token:
            logger.error("DESCOPE_BEARER_TOKEN environment variable not set")
            return
            
        # Extract project ID from bearer token (format: P2xxx:Key)
        try:
            self.project_id = self.bearer_token.split(':')[0]
            logger.info(f"Extracted project ID: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to extract project ID from bearer token: {e}")
            self.project_id = None
            
        # Base API URL
        self.base_url = "https://api.descope.com/v1"
        self.api_url = f"{self.base_url}/mgmt/user/search"
        
        # Configure SSL context
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        logger.info("Successfully initialized Descope service")
        logger.debug(f"Using Descope API URL: {self.api_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def get_total_users(self, date: Optional[datetime] = None) -> int:
        """Get total number of users from Descope.
        
        Args:
            date: Optional datetime to filter users by registration date
            
        Returns:
            int: Total number of users registered before or at the given date
            
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

            # Simplified query structure
            query = {
                "searchFilter": {},  # Empty filter to get all users
                "page": 1,
                "limit": 1,  # We only need the total count
                "options": {
                    "withTestUsers": False
                }
            }

            if date:
                # Convert date to milliseconds timestamp for Descope API
                date_ms = int(date.timestamp() * 1000)
                query["searchFilter"] = {
                    "filterFields": [{
                        "attributeKey": "createdTime",
                        "operator": "lte",
                        "value": date_ms
                    }]
                }
                logger.debug(f"Querying users created before: {date_ms}")

            logger.debug(f"Sending request to Descope with query: {query}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=query,
                    ssl=self.ssl_context,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Descope raw response: {response_text}")
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Log full response for debugging
                        logger.debug(f"Descope response data: {data}")
                        
                        # Get total directly from response
                        total_users = data.get('total', 0)
                        
                        # Log total users
                        logger.info(f"Total users found: {total_users}")
                        
                        if total_users == 0:
                            logger.warning("Received zero users from Descope - this may indicate an issue")
                            
                        return total_users
                    elif response.status == 401:
                        logger.error("Authentication failed - check DESCOPE_BEARER_TOKEN")
                        raise Exception("Descope authentication failed")
                    elif response.status == 403:
                        logger.error("Permission denied - check API token permissions")
                        raise Exception("Descope permission denied")
                    else:
                        error_msg = f"Failed to fetch users from Descope. Status: {response.status}, Error: {response_text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

        except aiohttp.ClientError as e:
            logger.error(f"Network error connecting to Descope: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error getting total users: {e}", exc_info=True)
            raise

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

    async def get_new_users_in_period(self, start_date: datetime, end_date: datetime) -> int:
        """Get the number of new users created in a specific time period."""
        try:
            if not self.bearer_token:
                logger.warning("Missing Descope bearer token, returning 0 users")
                return 0

            # Convert dates to UTC ISO format for Descope API
            start_ts = int(start_date.timestamp() * 1000)  # Convert to milliseconds
            end_ts = int(end_date.timestamp() * 1000)  # Convert to milliseconds

            query = {
                "searchFilter": {
                    "filterFields": [
                        {
                            "attributeKey": "createdTime",
                            "operator": "gte",
                            "value": start_ts
                        },
                        {
                            "attributeKey": "createdTime",
                            "operator": "lte",
                            "value": end_ts
                        }
                    ]
                },
                "page": 1,
                "limit": 1,
                "options": {
                    "withTestUsers": False
                }
            }

            logger.debug(f"Querying new users with filter: {query}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/mgmt/user/search",
                    headers={
                        "Authorization": f"Bearer {self.bearer_token}",
                        "Content-Type": "application/json"
                    },
                    json=query,
                    ssl=self.ssl_context
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Descope raw response: {response_text}")

                    if response.status == 200:
                        data = await response.json()
                        total = data.get('total', 0)
                        logger.info(f"Found {total} new users between {start_date} and {end_date}")
                        return total
                    else:
                        logger.error(f"Failed to get new users from Descope. Status: {response.status}")
                        return 0

        except Exception as e:
            logger.error(f"Error getting new users from Descope: {str(e)}")
            return 0

    async def get_users_list(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get list of users with optional date filtering.
        
        Args:
            start_date: Optional start date to filter users by creation date
            end_date: Optional end date to filter users by creation date
            
        Returns:
            List[Dict[str, Any]]: List of user details
        """
        try:
            if not self.bearer_token:
                logger.warning("Missing Descope bearer token, returning empty list")
                return []

            # Build filter fields if dates are provided
            filter_fields = []
            if start_date:
                filter_fields.append({
                    "attributeKey": "createdTime",
                    "operator": "gte",
                    "value": int(start_date.timestamp() * 1000)
                })
            if end_date:
                filter_fields.append({
                    "attributeKey": "createdTime",
                    "operator": "lte",
                    "value": int(end_date.timestamp() * 1000)
                })

            # Build query
            query = {
                "searchFilter": {
                    "filterFields": filter_fields
                } if filter_fields else {},
                "page": 1,
                "limit": 100,  # Get more users per page
                "options": {
                    "withTestUsers": False
                }
            }

            users = []
            total_pages = 1
            current_page = 1

            while current_page <= total_pages:
                query["page"] = current_page
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/mgmt/user/search",
                        headers={
                            "Authorization": f"Bearer {self.bearer_token}",
                            "Content-Type": "application/json"
                        },
                        json=query,
                        ssl=self.ssl_context
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            users.extend(data.get('users', []))
                            
                            # Update total pages if this is the first request
                            if current_page == 1:
                                total = data.get('total', 0)
                                total_pages = (total + query["limit"] - 1) // query["limit"]
                            
                            current_page += 1
                        else:
                            error_text = await response.text()
                            logger.error(f"Failed to get users list. Status: {response.status}, Error: {error_text}")
                            break

            return users

        except Exception as e:
            logger.error(f"Error getting users list: {str(e)}")
            return []

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
                logger.warning("Missing Descope bearer token, returning empty details")
                return {}

            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }

            user_details = {}
            for user_id in user_ids:
                url = f"{self.base_url}/mgmt/user/{user_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        ssl=self.ssl_context,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            user = data.get('user', {})
                            user_details[user_id] = {
                                'email': user.get('email'),
                                'name': user.get('name'),
                                'createdTime': user.get('createdTime')
                            }
                        else:
                            logger.warning(f"Failed to fetch details for user {user_id}")

            return user_details

        except aiohttp.ClientError as e:
            logger.error(f"Network error connecting to Descope: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"Error getting user details: {e}", exc_info=True)
            return {}

    async def search_users(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for users using the Descope search API.
        
        Args:
            query: Search query parameters
            
        Returns:
            List[Dict[str, Any]]: List of matching users
        """
        try:
            if not self.bearer_token:
                logger.warning("Missing Descope bearer token")
                return []

            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/mgmt/user/search",
                    headers=headers,
                    json=query,
                    ssl=self.ssl_context,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('users', [])
                        logger.info(f"Found {len(users)} users in Descope search")
                        return users
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to search users. Status: {response.status}, Error: {error_text}")
                        return []

        except aiohttp.ClientError as e:
            logger.error(f"Network error searching users: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error searching users: {e}", exc_info=True)
            return []