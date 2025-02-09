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
import json
import asyncio

logger = logging.getLogger(__name__)

class DescopeService:
    """Service for interacting with Descope API"""

    def __init__(self):
        """Initialize the Descope service"""
        self.base_url = "https://api.descope.com"
        raw_token = os.getenv('DESCOPE_BEARER_TOKEN')
        
        if not raw_token:
            logger.error("Missing DESCOPE_BEARER_TOKEN environment variable")
            return
            
        # Split token into project ID and key
        try:
            self.project_id, self.bearer_token = raw_token.split(':')
            logger.info(f"Initialized Descope service with project ID: {self.project_id}")
        except ValueError:
            logger.error("Invalid DESCOPE_BEARER_TOKEN format. Expected format: PROJECT_ID:TOKEN")
            return
        
        # Configure SSL context for Descope API
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        self.ssl_context.load_verify_locations(cafile=certifi.where())
        
        # Configure connector with SSL context
        self.connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        self.session = None

        # Configure headers
        self.headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
            'Descope-Project-Id': self.project_id
        }
        
        logger.info("Successfully initialized Descope service")
        logger.debug(f"Using Descope API URL: {self.base_url}")

    async def get_session(self):
        """Get or create an aiohttp ClientSession"""
        if self.session is None or self.session.closed:
            logger.info("Creating new aiohttp ClientSession")
            self.session = aiohttp.ClientSession(connector=self.connector)
        return self.session

    async def close(self):
        """Close the session and connector if they exist"""
        if self.session and not self.session.closed:
            logger.info("Closing aiohttp ClientSession")
            await self.session.close()
        if self.connector and not self.connector.closed:
            logger.info("Closing TCP connector")
            await self.connector.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
            if not self.bearer_token or not self.project_id:
                logger.error("Missing authentication credentials")
                return 0

            headers = self.headers

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

            session = await self.get_session()
            async with session.post(
                f"{self.base_url}/v1/mgmt/user/search",
                headers=headers,
                json=query,
                timeout=30
            ) as response:
                response_text = await response.text()
                logger.debug(f"Descope raw response: {response_text}")
                
                if response.status == 200:
                    data = await response.json()
                    total_users = data.get('total', 0)
                    logger.info(f"Total users found: {total_users}")
                    return total_users
                elif response.status == 401:
                    logger.error("Authentication failed - check DESCOPE_BEARER_TOKEN format and values")
                    raise Exception("Descope authentication failed - invalid credentials")
                elif response.status == 403:
                    logger.error("Permission denied - check API token permissions")
                    raise Exception("Descope permission denied - insufficient permissions")
                else:
                    error_msg = f"Failed to fetch users from Descope. Status: {response.status}, Error: {response_text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

        except aiohttp.ClientError as e:
            logger.error(f"Network error connecting to Descope: {e}", exc_info=True)
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting total users: {str(e)}", exc_info=True)
            raise

    async def get_active_users(self, start_date: datetime, end_date: datetime) -> int:
        """Get number of active users in date range"""
        if not self.bearer_token:
            logger.error("Missing Descope credentials")
            return 0

        try:
            headers = self.headers
            
            query = {
                "pageSize": 1,
                "page": 1,
                "loginTime": {
                    "after": start_date.isoformat(),
                    "before": end_date.isoformat()
                }
            }

            session = await self.get_session()
            async with session.post(f"{self.base_url}/v1/mgmt/user/activity", headers=headers, json=query) as response:
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

            session = await self.get_session()
            async with session.post(
                f"{self.base_url}/v1/mgmt/user/search",
                headers=self.headers,
                json=query
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
                
                session = await self.get_session()
                async with session.post(
                    f"{self.base_url}/v1/mgmt/user/search",
                    headers=self.headers,
                    json=query
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

    async def get_user_details(self, trace_ids: List[str]) -> Dict[str, Dict]:
        """Get user details from Descope based on v2UserId"""
        if not trace_ids:
            return {}

        logger.info(f"Getting user details for {len(trace_ids)} users")
        
        # Build query to search for users with matching v2UserIds
        query = {
            "searchFilter": {
                "filterFields": [{
                    "attributeKey": "customAttributes.v2UserId",
                    "operator": "in",
                    "values": trace_ids
                }]
            },
            "page": 1,
            "limit": len(trace_ids),
            "options": {
                "withTestUsers": False
            }
        }

        max_retries = 3
        retry_delay = 1  # Initial delay in seconds

        for attempt in range(max_retries):
            try:
                session = await self.get_session()
                async with session.post(
                    f"{self.base_url}/v1/mgmt/user/search",
                    headers=self.headers,
                    json=query,
                    timeout=30  # Add explicit timeout
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Descope raw response (attempt {attempt + 1}): {response_text}")

                    if response.status == 200:
                        data = await response.json()
                        users = data.get('users', [])
                        
                        # Create mapping of v2UserId to user details
                        user_details = {}
                        for user in users:
                            custom_attrs = user.get('customAttributes', {})
                            v2_user_id = custom_attrs.get('v2UserId')
                            if v2_user_id:
                                # Get email from multiple possible locations
                                email = user.get('email', '')
                                if not email:
                                    # Try alternate locations
                                    email = (
                                        user.get('loginIds', [None])[0] or  # First login ID
                                        custom_attrs.get('email', '') or    # Custom attribute
                                        user.get('externalIds', {}).get('email', '')  # External ID
                                    )
                                
                                user_details[v2_user_id] = {
                                    'email': email,
                                    'name': user.get('name', ''),
                                    'displayName': user.get('displayName', ''),
                                    'createdTime': user.get('createdTime', 0),
                                    'loginIds': user.get('loginIds', []),
                                    'customAttributes': custom_attrs
                                }
                        
                        # Log found users and any missing ones
                        found_ids = set(user_details.keys())
                        missing_ids = set(trace_ids) - found_ids
                        logger.info(f"Found details for {len(user_details)} out of {len(trace_ids)} users")
                        if missing_ids:
                            logger.warning(f"Missing user details for IDs: {missing_ids}")
                        
                        return user_details
                    
                    elif response.status == 401:
                        logger.error("Authentication failed with Descope API. Check your bearer token and project ID.")
                        return {}
                    
                    elif response.status == 429:  # Rate limit
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Rate limited by Descope API. Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error("Max retries reached after rate limiting")
                            return {}
                    
                    else:
                        logger.error(f"Failed to get user details. Status: {response.status}, Response: {response_text}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        return {}

            except asyncio.TimeoutError:
                logger.error(f"Timeout while getting user details (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return {}
                
            except Exception as e:
                logger.error(f"Error getting user details: {str(e)}", exc_info=True)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return {}

        return {}  # Return empty dict if all retries failed

    async def post(self, path, data):
        """Make a POST request to Descope API"""
        session = await self.get_session()
        async with session.post(
            f"{self.base_url}{path}",
            headers=self.headers,
            json=data
        ) as response:
            response_text = await response.text()
            logger.debug(f"Descope raw response: {response_text}")
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to post to Descope. Status: {response.status}, Error: {response_text}")
                raise Exception(f"Failed to post to Descope. Status: {response.status}, Error: {response_text}")