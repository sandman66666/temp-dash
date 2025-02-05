"""
Activity metrics calculations (threads, sketches, renders)
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from src.services.analytics.metrics.base import BaseMetrics
from src.services.analytics.metrics.utils import get_empty_metric

logger = logging.getLogger(__name__)

class ActivityMetrics(BaseMetrics):
    """Handles activity-related metrics calculations"""

    async def get_thread_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users with message threads in time range"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self._get_date_range_query(start_date, end_date, "handleMessageInThread_start")

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting thread users"
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
            logger.error(f"Error getting thread users: {str(e)}", exc_info=True)
            return get_empty_metric()

    async def get_sketch_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users who have uploaded sketches in time range"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self._get_date_range_query(start_date, end_date, "uploadSketch_end")

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting sketch users"
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
            logger.error(f"Error getting sketch users: {str(e)}", exc_info=True)
            return get_empty_metric()

    async def get_render_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users who have completed renders in time range"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self._get_date_range_query(start_date, end_date, "renderStart_end")

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting render users"
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
            logger.error(f"Error getting render users: {str(e)}", exc_info=True)
            return get_empty_metric()

    async def get_medium_chat_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get users with 5-20 message threads in time range"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_thread_count_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                self.query_builder.build_date_range_filter(start_date, end_date)
            ],
            min_count=5,
            max_count=20
        )

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting medium chat users"
            )
            count = len(result["aggregations"]["thread_count"]["buckets"])
            daily_average = self._calculate_daily_average(count, start_date, end_date)
            
            return {
                "value": count,
                "previousValue": 0,
                "trend": "up" if count > 0 else "neutral",
                "changePercentage": 0,
                "daily_average": daily_average
            }
        except Exception as e:
            logger.error(f"Error getting medium chat users: {str(e)}", exc_info=True)
            return get_empty_metric()

    async def get_power_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get users with more than 20 message threads in time range"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_thread_count_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                self.query_builder.build_date_range_filter(start_date, end_date)
            ],
            min_count=20
        )

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting power users"
            )
            count = len(result["aggregations"]["thread_count"]["buckets"])
            daily_average = self._calculate_daily_average(count, start_date, end_date)
            
            return {
                "value": count,
                "previousValue": 0,
                "trend": "up" if count > 0 else "neutral",
                "changePercentage": 0,
                "daily_average": daily_average
            }
        except Exception as e:
            logger.error(f"Error getting power users: {str(e)}", exc_info=True)
            return get_empty_metric()

    async def get_thread_user_details(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get details for users with message threads"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
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
                "Error getting thread user details"
            )

            users = []
            for bucket in result["aggregations"]["users"]["buckets"]:
                user_id = bucket["key"]
                message_count = bucket["doc_count"]
                if message_count > 0:  # Only include users with messages
                    users.append({
                        "trace_id": user_id,
                        "messageCount": message_count
                    })

            return await self._get_user_details(users)

        except Exception as e:
            logger.error(f"Error getting thread user details: {str(e)}", exc_info=True)
            return []

    async def get_sketch_user_details(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get details for users who have uploaded sketches"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "uploadSketch_end"}},
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
                "Error getting sketch user details"
            )

            users = []
            for bucket in result["aggregations"]["users"]["buckets"]:
                user_id = bucket["key"]
                sketch_count = bucket["doc_count"]
                if sketch_count > 0:
                    users.append({
                        "trace_id": user_id,
                        "sketchCount": sketch_count
                    })

            return await self._get_user_details(users)

        except Exception as e:
            logger.error(f"Error getting sketch user details: {str(e)}", exc_info=True)
            return []

    async def get_render_user_details(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get details for users who have completed renders"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "renderStart_end"}},
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
                "Error getting render user details"
            )

            users = []
            for bucket in result["aggregations"]["users"]["buckets"]:
                user_id = bucket["key"]
                render_count = bucket["doc_count"]
                if render_count > 0:
                    users.append({
                        "trace_id": user_id,
                        "renderCount": render_count
                    })

            return await self._get_user_details(users)

        except Exception as e:
            logger.error(f"Error getting render user details: {str(e)}", exc_info=True)
            return []

    async def get_medium_chat_user_details(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get details for users with 5-20 message threads"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_thread_count_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                self.query_builder.build_date_range_filter(start_date, end_date)
            ],
            min_count=5,
            max_count=20
        )

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting medium chat user details"
            )

            users = []
            for bucket in result["aggregations"]["thread_count"]["buckets"]:
                user_id = bucket["key"]
                thread_count = bucket["doc_count"]
                users.append({
                    "trace_id": user_id,
                    "threadCount": thread_count
                })

            return await self._get_user_details(users)

        except Exception as e:
            logger.error(f"Error getting medium chat user details: {str(e)}", exc_info=True)
            return []

    async def get_power_user_details(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get details for users with more than 20 message threads"""
        start_date, end_date = self._validate_dates(start_date, end_date)
        query = self.query_builder.build_thread_count_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                self.query_builder.build_date_range_filter(start_date, end_date)
            ],
            min_count=20
        )

        try:
            result = await self._execute_opensearch_query(
                query,
                "Error getting power user details"
            )

            users = []
            for bucket in result["aggregations"]["thread_count"]["buckets"]:
                user_id = bucket["key"]
                thread_count = bucket["doc_count"]
                users.append({
                    "trace_id": user_id,
                    "threadCount": thread_count
                })

            return await self._get_user_details(users)

        except Exception as e:
            logger.error(f"Error getting power user details: {str(e)}", exc_info=True)
            return []