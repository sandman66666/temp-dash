"""
AnalyticsService: Core service for fetching and aggregating analytics data
"""
from typing import Dict, Any
import logging
import asyncio
import ssl
import certifi
import aiohttp
import json
from datetime import datetime, timedelta
from opensearchpy import AsyncOpenSearch
import redis.asyncio as redis
import os
from src.utils.query_builder import OpenSearchQueryBuilder

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, opensearch_client: AsyncOpenSearch, redis_client: redis.Redis):
        self.opensearch = opensearch_client
        self.redis = redis_client
        self.index = "events-v2"
        self.cache_ttl = timedelta(minutes=5)
        self.query_builder = OpenSearchQueryBuilder()
        # Based on your mapping, the timestamp field is "timestamp"
        self.timestamp_field = "timestamp"
        # Set this environment variable to "true" to disable caching for testing.
        self.disable_cache = os.getenv('DISABLE_CACHE', 'false').lower() == 'true'

    def _format_date_os(self, dt: datetime) -> int:
        """
        Format the datetime to epoch milliseconds (for OpenSearch queries).
        Returns an integer.
        """
        epoch_ms = int(dt.timestamp() * 1000)
        logger.debug("Formatted %s to epoch ms: %s", dt, epoch_ms)
        return epoch_ms

    def _format_date_iso(self, dt: datetime) -> str:
        """
        Format the datetime to an ISO string (for caching and external APIs).
        """
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_dashboard_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get all metrics needed for the dashboard.
        Uses Redis cache with OpenSearch as the source of truth unless caching is disabled.
        """
        cache_key = f"dashboard_metrics_{self._format_date_iso(start_date)}_{self._format_date_iso(end_date)}"
        
        if not self.disable_cache:
            # Try to get from cache first
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                logger.debug("Returning cached metrics for key: %s", cache_key)
                return json.loads(cached_data)
        else:
            logger.debug("Caching is disabled. Bypassing Redis cache.")

        try:
            # Get all required metrics concurrently with time filters
            descope_users, thread_users, sketch_users, render_users, medium_users, power_users = await asyncio.gather(
                self._get_total_users(start_date, end_date),
                self._get_thread_users(start_date, end_date),
                self._get_sketch_users(start_date, end_date),
                self._get_render_users(start_date, end_date),
                self._get_medium_chat_users(start_date, end_date),
                self._get_power_users(start_date, end_date)
            )

            metrics = {
                "status": "success",
                "data": {
                    "descope_users": descope_users,
                    "thread_users": thread_users,
                    "sketch_users": sketch_users,
                    "render_users": render_users,
                    "medium_chat_users": medium_users,
                    "active_chat_users": power_users
                },
                "timeRange": {
                    "start": self._format_date_iso(start_date),
                    "end": self._format_date_iso(end_date)
                }
            }

            if not self.disable_cache:
                await self.redis.set(
                    cache_key,
                    json.dumps(metrics),
                    ex=int(self.cache_ttl.total_seconds())
                )
                logger.debug("Cached metrics with key: %s", cache_key)
            else:
                logger.debug("Not caching metrics because caching is disabled.")

            return metrics

        except Exception as e:
            logger.error("Error fetching dashboard metrics: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timeRange": {
                    "start": self._format_date_iso(start_date),
                    "end": self._format_date_iso(end_date)
                }
            }

    async def _get_thread_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users with message threads"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }
        logger.debug("Thread Users range filter: %s", time_filter)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "unique_users": {"cardinality": {"field": "trace_id.keyword"}}
                }
            }
        )
        result = await self.opensearch.search(index=self.index, body=query, size=0)
        count = result["aggregations"]["unique_users"]["value"]
        logger.debug("Thread Users count: %s", count)
        return {
            "value": count,
            "label": "Thread Users",
            "description": "Users who have started at least one message thread"
        }

    async def _get_total_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get total number of users from Descope with time filter"""
        descope_url = os.getenv('DESCOPE_API_URL', 'https://api.descope.com/v1/mgmt/user/search')
        bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
        if not bearer_token:
            logger.error("Descope bearer token not found in environment variables")
            return {"value": 0, "label": "Total Users", "description": "Error: Could not fetch user count"}
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "tenantIds": [],
            "text": "",
            "roleNames": [],
            "loginIds": [],
            "ssoAppIds": [],
            "customAttributes": {},
            "startDate": self._format_date_iso(start_date),
            "endDate": self._format_date_iso(end_date)
        }
        logger.debug("Descope payload: %s", payload)
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        try:
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.post(descope_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('users', [])
                        total_count = len(users)
                        logger.debug("Descope users count: %s", total_count)
                        return {
                            "value": total_count,
                            "label": "Total Users",
                            "description": "Total number of registered users",
                            "previousValue": total_count - (total_count * 0.1)
                        }
                    else:
                        error_text = await response.text()
                        logger.error("Descope API error: %s - %s", response.status, error_text)
                        return {
                            "value": 0,
                            "label": "Total Users",
                            "description": f"Error: {response.status}"
                        }
        except Exception as e:
            logger.error("Error fetching Descope users: %s", str(e))
            return {"value": 0, "label": "Total Users", "description": f"Error: {str(e)}"}

    async def _get_sketch_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users who have uploaded sketches"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }
        logger.debug("Sketch Users range filter: %s", time_filter)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "uploadSketch_end"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "unique_users": {"cardinality": {"field": "trace_id.keyword"}}
                }
            }
        )
        result = await self.opensearch.search(index=self.index, body=query, size=0)
        count = result["aggregations"]["unique_users"]["value"]
        logger.debug("Sketch Users count: %s", count)
        return {
            "value": count,
            "label": "Sketch Users",
            "description": "Users who have uploaded at least one sketch"
        }

    async def _get_render_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of users who have completed renders"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }
        logger.debug("Render Users range filter: %s", time_filter)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "renderStart_end"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "unique_users": {"cardinality": {"field": "trace_id.keyword"}}
                }
            }
        )
        result = await self.opensearch.search(index=self.index, body=query, size=0)
        count = result["aggregations"]["unique_users"]["value"]
        logger.debug("Render Users count: %s", count)
        return {
            "value": count,
            "label": "Render Users",
            "description": "Users who have completed at least one render"
        }

    async def _get_medium_chat_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get users with 5-20 message threads"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }
        logger.debug("Medium Chat Users range filter: %s", time_filter)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "thread_count": {
                        "terms": {"field": "trace_id.keyword", "size": 10000},
                        "aggs": {
                            "thread_filter": {
                                "bucket_selector": {
                                    "buckets_path": {"count": "_count"},
                                    "script": "params.count >= 5 && params.count <= 20"
                                }
                            }
                        }
                    }
                }
            }
        )
        result = await self.opensearch.search(index=self.index, body=query, size=0)
        count = len(result["aggregations"]["thread_count"]["buckets"])
        logger.debug("Medium Chat Users count: %s", count)
        return {
            "value": count,
            "label": "Medium Activity Users",
            "description": "Users with 5-20 message threads"
        }

    async def _get_power_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get users with more than 20 message threads"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }
        logger.debug("Power Users range filter: %s", time_filter)
        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "thread_count": {
                        "terms": {"field": "trace_id.keyword", "size": 10000},
                        "aggs": {
                            "thread_filter": {
                                "bucket_selector": {
                                    "buckets_path": {"count": "_count"},
                                    "script": "params.count > 20"
                                }
                            }
                        }
                    }
                }
            }
        )
        result = await self.opensearch.search(index=self.index, body=query, size=0)
        count = len(result["aggregations"]["thread_count"]["buckets"])
        logger.debug("Power Users count: %s", count)
        return {
            "value": count,
            "label": "Power Users",
            "description": "Users with more than 20 message threads"
        }