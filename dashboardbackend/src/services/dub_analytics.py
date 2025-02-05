"""
Analytics service for user activity analysis
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from opensearchpy import AsyncOpenSearch
import redis.asyncio as redis
import os
import ssl
import certifi
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Analytics service for user activity"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch, redis_client: redis.Redis):
        self.opensearch = opensearch_client
        self.redis = redis_client
        self.index = "events-v2"
        self.cache_ttl = timedelta(minutes=5)
        self.disable_cache = os.getenv('DISABLE_CACHE', 'false').lower() == 'true'
        self.request_timeout = int(os.getenv('MAX_QUERY_TIME', '30'))
        self.min_date = datetime(2024, 10, 1, tzinfo=timezone.utc)

        self._configure_opensearch()

    def _configure_opensearch(self):
        """Configure OpenSearch client with SSL and authentication"""
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        self.opensearch._ssl_context = ssl_context
        self.opensearch.use_ssl = True
        self.opensearch.verify_certs = False
        self.opensearch.ssl_assert_hostname = False
        self.opensearch.ssl_show_warn = True

    async def get_user_activity(self, start_date: datetime, end_date: datetime, filter_type: str) -> Dict[str, Any]:
        """Get user activity based on filter type"""
        logger.info(f"Getting user activity: start={start_date}, end={end_date}, filter={filter_type}")

        # Ensure dates are timezone-aware
        start_date = self._ensure_timezone(start_date)
        end_date = self._ensure_timezone(end_date)

        # Ensure no data before Oct 1st 2024
        if start_date < self.min_date:
            start_date = self.min_date

        cache_key = f"user_activity_{self._format_date_iso(start_date)}_{self._format_date_iso(end_date)}_{filter_type}"
        
        if not self.disable_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

        try:
            # Build OpenSearch query
            must_conditions = [
                {"range": {"timestamp": {
                    "gte": int(start_date.timestamp() * 1000),
                    "lte": int(end_date.timestamp() * 1000)
                }}}
            ]

            # Add filter for successful events only
            must_conditions.append({"term": {"status.keyword": "succeeded"}})

            # Build aggregation for user activity
            aggs = {
                "users": {
                    "terms": {
                        "field": "trace_id.keyword",
                        "size": 10000
                    },
                    "aggs": {
                        "actions": {
                            "date_histogram": {
                                "field": "timestamp",
                                "calendar_interval": "day"
                            }
                        },
                        "first_action": {"min": {"field": "timestamp"}},
                        "last_action": {"max": {"field": "timestamp"}},
                        "user_email": {
                            "terms": {
                                "field": "email.keyword",
                                "size": 1
                            }
                        }
                    }
                }
            }

            query = {
                "query": {"bool": {"must": must_conditions}},
                "aggs": aggs,
                "size": 0
            }

            # Execute query
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                request_timeout=self.request_timeout
            )

            # Process results
            users = []
            for bucket in result["aggregations"]["users"]["buckets"]:
                user_id = bucket["key"]
                email = bucket["user_email"]["buckets"][0]["key"] if bucket["user_email"]["buckets"] else "Unknown"
                first_action = bucket["first_action"]["value"]
                last_action = bucket["last_action"]["value"]
                total_actions = bucket["doc_count"]
                days_between = (last_action - first_action) / (1000 * 60 * 60 * 24)  # Convert ms to days

                # Filter users based on activity pattern
                include_user = False
                if filter_type == "consecutive_days":
                    # Check if user has actions on consecutive days
                    action_dates = set(
                        datetime.fromtimestamp(hit["key"] / 1000, tz=timezone.utc).date()
                        for hit in bucket["actions"]["buckets"]
                    )
                    consecutive_days = any(
                        date + timedelta(days=1) in action_dates
                        for date in action_dates
                    )
                    include_user = consecutive_days
                elif filter_type == "one_to_two_weeks":
                    include_user = 7 <= days_between <= 14
                elif filter_type == "two_to_three_weeks":
                    include_user = 14 < days_between <= 21
                elif filter_type == "month_apart":
                    include_user = days_between >= 28

                if include_user and total_actions >= 2:
                    users.append({
                        "trace_id": user_id,
                        "email": email,
                        "firstAction": datetime.fromtimestamp(first_action / 1000, tz=timezone.utc).isoformat(),
                        "lastAction": datetime.fromtimestamp(last_action / 1000, tz=timezone.utc).isoformat(),
                        "daysBetween": round(days_between, 1),
                        "totalActions": total_actions
                    })

            # Sort users by total actions descending
            users.sort(key=lambda x: x["totalActions"], reverse=True)

            response_data = {
                "status": "success",
                "users": users,
                "timeRange": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

            if not self.disable_cache:
                await self._save_to_cache(cache_key, response_data)

            return response_data

        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }

    def _ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime has UTC timezone"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _format_date_iso(self, dt: datetime) -> str:
        """Format datetime to ISO string"""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get data from Redis cache"""
        try:
            data = await self.redis.get(key)
            return data if data is None else data
        except Exception as e:
            logger.warning(f"Redis cache retrieval failed: {str(e)}")
            return None

    async def _save_to_cache(self, key: str, data: Dict) -> None:
        """Save data to Redis cache"""
        try:
            await self.redis.set(
                key,
                data,
                ex=int(self.cache_ttl.total_seconds())
            )
        except Exception as e:
            logger.warning(f"Redis cache storage failed: {str(e)}")