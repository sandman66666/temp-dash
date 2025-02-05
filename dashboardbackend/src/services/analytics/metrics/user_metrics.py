"""
User-related metrics calculations (total users, producers)
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from src.services.analytics.metrics.base import BaseMetrics
from src.services.analytics.metrics.utils import get_empty_metric

logger = logging.getLogger(__name__)

class UserMetrics(BaseMetrics):
    """Handles user-related metrics calculations"""

    async def get_total_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get total users count within date range"""
        start_date, end_date = self._validate_dates(start_date, end_date)

        try:
            # Only get Descope users if the period includes time after Jan 27, 2025
            if end_date >= self.descope_start_date:
                descope_start = max(start_date, self.descope_start_date)
                users_data = await self.descope.get_total_users(end_date, descope_start)
                logger.info(f"Got {users_data['value']} Descope users")
                return users_data
            
            logger.info("Date range before Descope start date, returning 0")
            return get_empty_metric()

        except Exception as e:
            logger.error(f"Error getting total users: {str(e)}", exc_info=True)
            return get_empty_metric()

    async def get_producers(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of producers in time range"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self._get_date_range_query(start_date, end_date, "producer_activity")

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting producers"
            )
            count = result["aggregations"]["unique_users"]["value"]
            daily_average = self._calculate_daily_average(count, start_date, end_date)
            
            return {
                "value": count,
                "previousValue": 0,
                "trend": "up" if count > 0 else "neutral",
                "changePercentage": 0,
                "daily_average": daily_average
            }
        except Exception as e:
            logger.error(f"Error getting producers: {str(e)}", exc_info=True)
            return get_empty_metric()

    async def get_descope_user_details(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get details for Descope users"""
        start_date, end_date = self._validate_dates(start_date, end_date)

        # Only get Descope users if after Jan 27, 2025
        if end_date < self.descope_start_date:
            logger.info("Date range before Descope start date, returning empty list")
            return []

        start_date = max(start_date, self.descope_start_date)

        try:
            # First get user IDs from OpenSearch for the date range
            query = self.query_builder.build_composite_query(
                must_conditions=[
                    {"range": {"timestamp": {
                        "gte": self._format_date_os(start_date),
                        "lte": self._format_date_os(end_date)
                    }}}
                ],
                aggregations={
                    "users": {
                        "terms": {
                            "field": "trace_id.keyword",
                            "size": 10000
                        }
                    }
                }
            )

            result = await self._execute_opensearch_query(
                query,
                "Error getting user IDs from OpenSearch"
            )

            user_ids = [bucket["key"] for bucket in result["aggregations"]["users"]["buckets"]]
            if not user_ids:
                logger.info("No users found in OpenSearch")
                return []

            # Get detailed user information from Descope
            user_details = await self.descope.get_user_details(user_ids)
            if not user_details:
                logger.info("No user details found in Descope")
                return []
            
            users = []
            for user_id, details in user_details.items():
                users.append({
                    "trace_id": user_id,
                    "email": details.get("email", "Unknown"),
                    "name": details.get("name", "Unknown"),
                    "lastLoginTime": details.get("lastLoginTime", ""),
                    "createdTime": details.get("createdTime", "")
                })

            logger.info(f"Found {len(users)} users with details")
            return users

        except Exception as e:
            logger.error(f"Error getting Descope user details: {str(e)}", exc_info=True)
            return []

    async def get_producer_details(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get details for producers"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "producer_activity"}},
                self.query_builder.build_date_range_filter(start_date, end_date)
            ],
            aggregations={
                "users": {
                    "terms": {
                        "field": "trace_id.keyword",
                        "size": 10000
                    }
                }
            }
        )

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting producer details"
            )

            users = []
            for bucket in result["aggregations"]["users"]["buckets"]:
                user_id = bucket["key"]
                activity_count = bucket["doc_count"]
                if activity_count > 0:
                    users.append({
                        "trace_id": user_id,
                        "activityCount": activity_count
                    })

            if not users:
                logger.info("No producers found")
                return []

            # Get user details from Descope
            user_ids = [user["trace_id"] for user in users]
            user_details = await self.descope.get_user_details(user_ids)

            # Combine activity counts with user details
            detailed_users = []
            for user in users:
                user_id = user["trace_id"]
                if user_id in user_details:
                    detailed_users.append({
                        **user,
                        "email": user_details[user_id].get("email", "Unknown"),
                        "name": user_details[user_id].get("name", "Unknown"),
                        "lastLoginTime": user_details[user_id].get("lastLoginTime", ""),
                        "createdTime": user_details[user_id].get("createdTime", "")
                    })

            logger.info(f"Found {len(detailed_users)} producers with details")
            return detailed_users

        except Exception as e:
            logger.error(f"Error getting producer details: {str(e)}", exc_info=True)
            return []

    def _get_date_range_query(self, start_date: datetime, end_date: datetime, event_name: str) -> Dict:
        """Build query with date range and event name"""
        return self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": event_name}},
                {"range": {"timestamp": {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }}}
            ],
            aggregations={
                "unique_users": {
                    "cardinality": {
                        "field": "trace_id.keyword"
                    }
                }
            }
        )