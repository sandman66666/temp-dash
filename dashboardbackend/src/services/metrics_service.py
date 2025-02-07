"""
Consolidated metrics service for analytics
"""
from typing import Dict, Any
import logging
from datetime import datetime
from src.utils.query_builder import OpenSearchQueryBuilder
from src.services.analytics.metrics.base import BaseMetricsService
from src.services.descope_service import DescopeService
from src.services.caching_service import CachingService

logger = logging.getLogger(__name__)

class AnalyticsMetricsService(BaseMetricsService):
    def __init__(self, opensearch_client, caching_service: CachingService, query_builder: OpenSearchQueryBuilder, index: str, timestamp_field: str, request_timeout: int, descope_service: DescopeService):
        super().__init__(opensearch_client, query_builder, index, timestamp_field, request_timeout, descope_service)
        self.caching_service = caching_service

    async def get_thread_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users with message threads in time range"""
        logger.info(f"Fetching thread users for date range: {start_date} to {end_date}")
        query = self._get_date_range_query(start_date, end_date, "handleMessageInThread_start")
        result = await self._execute_query(query, "thread users", start_date, end_date, "engagement")
        logger.info(f"Thread users result: {result}")
        return result

    async def get_medium_chat_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get users with 5-20 message threads in time range"""
        logger.info(f"Fetching medium chat users for date range: {start_date} to {end_date}")
        query = self._get_date_range_query(start_date, end_date, "handleMessageInThread_start")
        query.update(self._build_thread_count_aggregation(min_count=5, max_count=20))
        result = await self._execute_query(query, "medium chat users", start_date, end_date, "engagement")
        logger.info(f"Medium chat users result: {result}")
        return result

    async def get_power_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get users with more than 20 message threads in time range"""
        logger.info(f"Fetching power users for date range: {start_date} to {end_date}")
        query = self._get_date_range_query(start_date, end_date, "handleMessageInThread_start")
        query.update(self._build_thread_count_aggregation(min_count=21))
        result = await self._execute_query(query, "power users", start_date, end_date, "engagement")
        logger.info(f"Power users result: {result}")
        return result

    async def get_total_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get total number of users in time range"""
        logger.info(f"Fetching total users for date range: {start_date} to {end_date}")
        query = self._get_date_range_query(start_date, end_date)
        result = await self._execute_query(query, "total users", start_date, end_date, "user")
        logger.info(f"Total users result: {result}")
        return result

    async def get_producers(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of producers in time range"""
        logger.info(f"Fetching producers for date range: {start_date} to {end_date}")
        query = self._get_date_range_query(start_date, end_date, "producer_activity")
        result = await self._execute_query(query, "producers", start_date, end_date, "user")
        logger.info(f"Producers result: {result}")
        return result

    async def get_sketch_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users who have uploaded sketches in time range"""
        logger.info(f"Fetching sketch users for date range: {start_date} to {end_date}")
        query = self._get_date_range_query(start_date, end_date, "uploadSketch_end")
        result = await self._execute_query(query, "sketch users", start_date, end_date, "performance")
        logger.info(f"Sketch users result: {result}")
        return result

    async def get_render_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users who have completed renders in time range"""
        logger.info(f"Fetching render users for date range: {start_date} to {end_date}")
        query = self._get_date_range_query(start_date, end_date, "renderStart_end")
        result = await self._execute_query(query, "render users", start_date, end_date, "performance")
        logger.info(f"Render users result: {result}")
        return result

    async def fetch_metrics(self, start_date: datetime, end_date: datetime) -> None:
        """Fetch all metrics at once"""
        logger.info(f"Fetching all metrics for date range: {start_date} to {end_date}")
        start_date, end_date = self._validate_dates(start_date, end_date)
        self.thread_users = await self.get_thread_users(start_date, end_date)
        self.sketch_users = await self.get_sketch_users(start_date, end_date)
        self.render_users = await self.get_render_users(start_date, end_date)
        self.medium_chat_users = await self.get_medium_chat_users(start_date, end_date)
        self.power_users = await self.get_power_users(start_date, end_date)
        self.total_users = await self.get_total_users(start_date, end_date)
        self.producers = await self.get_producers(start_date, end_date)
        logger.info("Finished fetching all metrics")

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics"""
        metrics = {
            "thread_users": self.thread_users,
            "sketch_users": self.sketch_users,
            "render_users": self.render_users,
            "medium_chat_users": self.medium_chat_users,
            "power_users": self.power_users,
            "total_users": self.total_users,
            "producers": self.producers
        }
        logger.info(f"Returning metrics: {metrics}")
        return metrics

    def combine_with_historical_data(self, current_data: Dict[str, Any], historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine current metrics with historical data"""
        combined_data = current_data.copy()
        combined_data["value"] += historical_data.get("value", 0)
        combined_data["daily_average"] += historical_data.get("daily_average", 0)
        logger.info(f"Combined data: {combined_data}")
        return combined_data