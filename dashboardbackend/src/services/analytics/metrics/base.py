"""
Base class for metrics analytics
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from opensearchpy import AsyncOpenSearch, NotFoundError, RequestError

from src.utils.query_builder import OpenSearchQueryBuilder
from src.services.descope_service import DescopeService
from src.services.historical_data_service import HistoricalDataService
from src.services.analytics.metrics.utils import (
    ensure_timezone,
    calculate_delta,
    create_metric_object,
    get_empty_metric,
    format_date_iso
)

logger = logging.getLogger(__name__)

class BaseMetricsService:
    """Base class for all metrics calculations"""

    def __init__(self, 
                 opensearch_client: AsyncOpenSearch, 
                 query_builder: OpenSearchQueryBuilder, 
                 index: str,
                 timestamp_field: str,
                 request_timeout: int,
                 descope_service: DescopeService):
        self.opensearch = opensearch_client
        self.query_builder = query_builder
        self.index = index
        self.timestamp_field = timestamp_field
        self.request_timeout = request_timeout
        self.descope = descope_service
        self.history = HistoricalDataService()
        self.min_date = datetime(2024, 10, 1, tzinfo=timezone.utc)
        self.descope_start_date = datetime(2025, 1, 27, tzinfo=timezone.utc)

    async def _execute_opensearch_query(self, query: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Execute OpenSearch query with error handling"""
        try:
            logger.debug(f"Executing OpenSearch query: {query}")
            result = await self.opensearch.search(query=query, size=0)
            logger.debug(f"OpenSearch query result: {result}")
            return result
        except NotFoundError:
            logger.error(f"{error_message}: Index not found", exc_info=True)
            return self._get_empty_result()
        except RequestError as e:
            logger.error(f"{error_message}: Invalid query - {str(e)}", exc_info=True)
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"{error_message}: {str(e)}", exc_info=True)
            return self._get_empty_result()

    def _get_date_range_query(self, start_date: datetime, end_date: datetime, event_name: Optional[str] = None) -> Dict[str, Any]:
        """Build date range query for OpenSearch"""
        must_conditions = [self.query_builder.build_date_range_query(
            self._format_date_os(start_date),
            self._format_date_os(end_date)
        )]
        if event_name:
            must_conditions.append({"term": {"event_name.keyword": event_name}})

        return self.query_builder.build_composite_query(
            must_conditions=must_conditions,
            aggregations={
                "aggs": {
                    "unique_users": {"cardinality": {"field": "trace_id.keyword"}}
                }
            }
        )

    async def _get_user_details(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get user details from Descope"""
        if not users:
            return []

        try:
            user_ids = [user["trace_id"] for user in users]
            user_details = await self.descope.get_user_details(user_ids)

            # Merge Descope details with user stats
            detailed_users = []
            for user in users:
                details = user_details.get(user["trace_id"], {})
                detailed_user = {
                    **user,
                    "email": details.get("email", "Unknown"),
                    "name": details.get("name", "Unknown"),
                    "lastLoginTime": details.get("lastLoginTime", ""),
                    "createdTime": details.get("createdTime", "")
                }
                detailed_users.append(detailed_user)

            return detailed_users
        except Exception as e:
            logger.error(f"Error getting user details: {str(e)}", exc_info=True)
            return users  # Return original users without details rather than empty list

    def calculate_daily_average(self, total: float, start_date: datetime, end_date: datetime) -> float:
        """Calculate daily average for a metric"""
        days_in_range = (end_date - start_date).days + 1
        return total / days_in_range if days_in_range > 0 else 0

    def _validate_dates(self, start_date: datetime, end_date: datetime) -> Tuple[datetime, datetime]:
        """Validate and adjust date range"""
        start_date = ensure_timezone(start_date)
        end_date = ensure_timezone(end_date)

        if start_date < self.min_date:
            logger.info(f"Adjusting start date from {start_date} to min date {self.min_date}")
            start_date = self.min_date

        if start_date > end_date:
            logger.warning(f"Start date {start_date} is after end date {end_date}, swapping dates")
            start_date, end_date = end_date, start_date

        return start_date, end_date

    def _format_date_os(self, dt: datetime) -> int:
        """Format datetime for OpenSearch timestamp"""
        return int(dt.timestamp() * 1000)

    def _get_empty_result(self) -> Dict[str, Any]:
        """Get empty result structure for OpenSearch queries"""
        return {
            "aggregations": {
                "unique_users": {"value": 0},
                "users": {"buckets": []},
                "thread_count": {"buckets": []}
            }
        }

    def _build_user_aggregation(self, size: int = 10000) -> Dict[str, Any]:
        """Build user aggregation for OpenSearch queries"""
        return {
            "aggs": {
                "users": {
                    "terms": {
                        "field": "trace_id.keyword",
                        "size": size
                    }
                }
            }
        }

    def _build_thread_count_aggregation(self, min_count: Optional[int] = None, max_count: Optional[int] = None) -> Dict[str, Any]:
        """Build thread count aggregation for OpenSearch queries"""
        logger.info(f"Building thread count aggregation with min_count={min_count}, max_count={max_count}")
        aggs = {
            "thread_count": {
                "terms": {
                    "field": "trace_id.keyword",
                    "size": 10000
                },
                "aggs": {
                    "thread_count": {"value_count": {"field": "thread_id.keyword"}}
                }
            }
        }

        if min_count is not None or max_count is not None:
            script_parts = []
            if min_count is not None:
                script_parts.append(f"params.thread_count >= {min_count}")
            if max_count is not None:
                script_parts.append(f"params.thread_count <= {max_count}")

            aggs["thread_count"]["aggs"]["thread_filter"] = {
                "bucket_selector": {
                    "buckets_path": {"thread_count": "thread_count"},
                    "script": " && ".join(script_parts)
                }
            }

        logger.debug(f"Thread count aggregation: {aggs}")
        return {"aggs": aggs}

    def get_date_range(self, start_date: datetime, end_date: datetime) -> Dict[str, str]:
        """Get the date range for the metrics"""
        return {
            "start": format_date_iso(start_date),
            "end": format_date_iso(end_date)
        }

    def create_metric(self, value: float, previous_value: float, start_date: datetime, end_date: datetime, category: str) -> Dict[str, Any]:
        """Create a metric object with calculated daily average"""
        daily_average = self.calculate_daily_average(value, start_date, end_date)
        return create_metric_object(value, previous_value, daily_average, category, value)

    async def _execute_query(self, query: Dict[str, Any], metric_name: str, start_date: datetime, end_date: datetime, category: str) -> Dict[str, Any]:
        try:
            logger.info(f"Executing query for {metric_name}")
            logger.debug(f"Query: {query}")
            result = await self._execute_opensearch_query(query, f"Error getting {metric_name}")
            logger.debug(f"Raw result for {metric_name}: {result}")
            count = 0
        
            # Extract count from aggregations
            if "aggregations" in result:
                aggs = result["aggregations"]
                logger.debug(f"Aggregations for {metric_name}: {aggs}")
                if "unique_users" in aggs:
                    count = aggs["unique_users"]["value"]
                    logger.debug(f"{metric_name} unique users count: {count}")
                elif "users" in aggs and "buckets" in aggs["users"]:
                    count = len(aggs["users"]["buckets"])
                    logger.debug(f"{metric_name} users bucket count: {count}")
                elif "thread_count" in aggs and "buckets" in aggs["thread_count"]:
                    count = len([b for b in aggs["thread_count"]["buckets"] 
                            if "thread_filter" not in b or b["thread_count"]["value"] > 0])
                    logger.debug(f"{metric_name} thread count: {count}")
                    logger.debug(f"Thread count buckets: {aggs['thread_count']['buckets']}")
                else:
                    logger.warning(f"Unexpected aggregation structure for {metric_name}: {aggs}")
            else:
                logger.warning(f"No aggregations found in result for {metric_name}")

            logger.info(f"{metric_name} count: {count}")
            metric = self.create_metric(count, 0, start_date, end_date, category)
            logger.debug(f"Created metric for {metric_name}: {metric}")
            return metric
        except Exception as e:
            logger.error(f"Error getting {metric_name}: {str(e)}", exc_info=True)
            return self.create_metric(0, 0, start_date, end_date, category)