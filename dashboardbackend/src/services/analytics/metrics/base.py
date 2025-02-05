"""
Base class for metrics analytics
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from opensearchpy import AsyncOpenSearch, NotFoundError, RequestError

from src.services.analytics.queries import QueryBuilder
from src.services.analytics.descope import DescopeService
from src.services.analytics.historical import HistoricalDataService
from src.services.analytics.metrics.utils import (
    ensure_timezone,
    calculate_delta,
    create_metric_object,
    get_empty_metric,
    format_date_iso
)

logger = logging.getLogger(__name__)

class BaseMetrics:
    """Base class for all metrics calculations"""

    def __init__(self, 
                 opensearch_client: AsyncOpenSearch, 
                 query_builder: QueryBuilder, 
                 index: str,
                 descope_service: DescopeService):
        self.opensearch = opensearch_client
        self.query_builder = query_builder
        self.index = index
        self.descope = descope_service
        self.request_timeout = 30
        self.history = HistoricalDataService()
        self.min_date = datetime(2024, 10, 1, tzinfo=timezone.utc)
        self.descope_start_date = datetime(2025, 1, 27, tzinfo=timezone.utc)

    async def _execute_opensearch_query(self, query: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Execute OpenSearch query with error handling"""
        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
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

    def _get_date_range_query(self, start_date: datetime, end_date: datetime, event_name: str) -> Dict[str, Any]:
        """Build date range query for OpenSearch"""
        return self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": event_name}},
                self.query_builder.build_date_range_filter(start_date, end_date)
            ],
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

    def _calculate_daily_average(self, value: int, start_date: datetime, end_date: datetime) -> float:
        """Calculate daily average for a metric"""
        days_in_range = (end_date - start_date).days + 1
        return value / days_in_range if days_in_range > 0 else 0

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
        aggs = {
            "thread_count": {
                "terms": {
                    "field": "trace_id.keyword",
                    "size": 10000
                }
            }
        }

        if min_count is not None or max_count is not None:
            script_parts = []
            if min_count is not None:
                script_parts.append(f"params.count >= {min_count}")
            if max_count is not None:
                script_parts.append(f"params.count <= {max_count}")

            aggs["thread_count"]["aggs"] = {
                "thread_filter": {
                    "bucket_selector": {
                        "buckets_path": {"count": "_count"},
                        "script": " && ".join(script_parts)
                    }
                }
            }

        return {"aggs": aggs}