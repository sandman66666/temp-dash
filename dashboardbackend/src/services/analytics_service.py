"""
AnalyticsService: Core service for fetching and aggregating analytics data
"""
from typing import Dict, Any, List
import logging
import asyncio
from datetime import datetime, timedelta
from opensearchpy import AsyncOpenSearch, NotFoundError, RequestError
from opensearchpy.exceptions import ConnectionError, TransportError
import redis.asyncio as redis
import os
import json
import ssl
import certifi
import aiohttp
from src.utils.query_builder import OpenSearchQueryBuilder
from src.services.historical_data import HistoricalData

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, opensearch_client: AsyncOpenSearch, redis_client: redis.Redis):
        self.opensearch = opensearch_client
        self.redis = redis_client
        self.index = "events-v2"
        self.cache_ttl = timedelta(minutes=5)
        self.query_builder = OpenSearchQueryBuilder()
        self.timestamp_field = "timestamp"
        self.disable_cache = os.getenv('DISABLE_CACHE', 'false').lower() == 'true'
        self.max_retries = 3
        self.base_delay = 1  # Base delay in seconds
        self.request_timeout = int(os.getenv('MAX_QUERY_TIME', '30'))  # Request timeout in seconds

        # Configure OpenSearch client with authentication and SSL
        self.opensearch_url = os.getenv('OPENSEARCH_URL', 'https://localhost:9200')
        self.opensearch_username = os.getenv('OPENSEARCH_USERNAME')
        self.opensearch_password = os.getenv('OPENSEARCH_PASSWORD')
        
        # Configure SSL context for OpenSearch
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = False  # Disable hostname checking for localhost
        self.ssl_context.verify_mode = ssl.CERT_NONE  # Allow self-signed certificates for local development
        
        # Update OpenSearch client with authentication and SSL configuration
        self.opensearch._ssl_context = self.ssl_context
        self.opensearch.use_ssl = True
        self.opensearch.verify_certs = False  # Don't verify certs for local development
        self.opensearch.ssl_assert_hostname = False
        self.opensearch.ssl_show_warn = True
        
        # Set authentication credentials
        if self.opensearch_username and self.opensearch_password:
            self.opensearch.http_auth = (self.opensearch_username, self.opensearch_password)

    async def get_dashboard_metrics(self, start_date: datetime, end_date: datetime, include_v1: bool = True) -> Dict[str, Any]:
        """Get all metrics needed for the dashboard"""
        cache_key = f"dashboard_metrics_{self._format_date_iso(start_date)}_{self._format_date_iso(end_date)}_{include_v1}"
        
        if not self.disable_cache:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis cache retrieval failed: {str(e)}")

        try:
            # Get all metrics
            total_users = await self._get_total_users(start_date, end_date)
            thread_users = await self._get_thread_users(start_date, end_date)
            sketch_users = await self._get_sketch_users(start_date, end_date)
            render_users = await self._get_render_users(start_date, end_date)
            medium_users = await self._get_medium_chat_users(start_date, end_date)
            power_users = await self._get_power_users(start_date, end_date)
            producers = await self._get_producers(start_date, end_date)

            # Get V1 data if needed
            v1_data = HistoricalData.get_v1_metrics(start_date, end_date, include_v1)

            # Add V1 values directly to metrics
            if include_v1:
                total_users["value"] += v1_data["total_users"]
                thread_users["value"] += v1_data["active_users"]
                producers["value"] += v1_data["producers"]

            metrics = [
                {
                    "id": "descope_users",
                    "name": "Total Users",
                    "description": "Total number of registered users",
                    "category": "user",
                    "interval": "daily",
                    "data": total_users
                },
                {
                    "id": "thread_users",
                    "name": "Thread Users",
                    "description": "Users who have started at least one message thread",
                    "category": "engagement",
                    "interval": "daily",
                    "data": thread_users
                },
                {
                    "id": "render_users",
                    "name": "Render Users",
                    "description": "Users who have completed at least one render",
                    "category": "performance",
                    "interval": "daily",
                    "data": render_users
                },
                {
                    "id": "active_chat_users",
                    "name": "Power Users",
                    "description": "Users with more than 20 message threads",
                    "category": "engagement",
                    "interval": "daily",
                    "data": power_users
                },
                {
                    "id": "medium_chat_users",
                    "name": "Medium Activity Users",
                    "description": "Users with 5-20 message threads",
                    "category": "engagement",
                    "interval": "daily",
                    "data": medium_users
                },
                {
                    "id": "sketch_users",
                    "name": "Sketch Users",
                    "description": "Users who have uploaded at least one sketch",
                    "category": "performance",
                    "interval": "daily",
                    "data": sketch_users
                },
                {
                    "id": "producers",
                    "name": "Producers",
                    "description": "Total number of producers",
                    "category": "user",
                    "interval": "daily",
                    "data": producers
                }
            ]

            response = {
                "metrics": metrics,
                "timeRange": {
                    "start": self._format_date_iso(start_date),
                    "end": self._format_date_iso(end_date)
                }
            }

            if not self.disable_cache:
                try:
                    await self.redis.set(
                        cache_key,
                        json.dumps(response),
                        ex=int(self.cache_ttl.total_seconds())
                    )
                except Exception as e:
                    logger.warning(f"Redis cache storage failed: {str(e)}")

            return response

        except Exception as e:
            logger.error(f"Error fetching dashboard metrics: {str(e)}", exc_info=True)
            return {
                "metrics": [],
                "timeRange": {
                    "start": self._format_date_iso(start_date),
                    "end": self._format_date_iso(end_date)
                }
            }

    async def _get_producers(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get count of producers"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }

        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "producer_activity"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "unique_users": {"cardinality": {"field": "trace_id.keyword"}}
                }
            }
        )

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = result["aggregations"]["unique_users"]["value"]
            previous_count = int(count * 0.9)  # Simulated previous value
            change_percentage = ((count - previous_count) / previous_count * 100) if previous_count > 0 else 0
            return {
                "value": count,
                "previousValue": previous_count,
                "trend": "up" if count > previous_count else "down",
                "changePercentage": round(change_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting producers: {str(e)}")
            return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}

    async def get_user_statistics(self, start_date: datetime, end_date: datetime, gauge_type: str) -> List[Dict[str, Any]]:
        """Get user statistics including message and sketch counts"""
        try:
            # Get all counts in parallel
            message_counts, sketch_counts, render_counts = await asyncio.gather(
                self._get_user_message_counts(start_date, end_date),
                self._get_user_sketch_counts(start_date, end_date),
                self._get_user_render_counts(start_date, end_date)
            )
            
            # Get user details
            user_ids = list(set(
                list(message_counts.keys()) + 
                list(sketch_counts.keys()) + 
                list(render_counts.keys())
            ))
            user_details = await self._get_user_details(user_ids)
            
            # Combine all data
            user_stats = []
            for user_id in user_ids:
                if user_id in user_details:
                    user_stat = {
                        "email": user_details[user_id]["email"],
                        "trace_id": user_id,
                        "messageCount": message_counts.get(user_id, 0),
                        "sketchCount": sketch_counts.get(user_id, 0),
                        "renderCount": render_counts.get(user_id, 0)
                    }
                    
                    # Filter based on gauge type
                    should_include = False
                    if gauge_type == "thread_users" and user_stat["messageCount"] > 0:
                        should_include = True
                    elif gauge_type == "sketch_users" and user_stat["sketchCount"] > 0:
                        should_include = True
                    elif gauge_type == "render_users" and user_stat["renderCount"] > 0:
                        should_include = True
                    elif gauge_type == "medium_chat_users" and 5 <= user_stat["messageCount"] <= 20:
                        should_include = True
                    elif gauge_type == "active_chat_users" and user_stat["messageCount"] > 20:
                        should_include = True

                    if should_include:
                        user_stats.append(user_stat)
            
            # Sort users based on the relevant metric for the gauge type
            if gauge_type == "thread_users" or gauge_type == "medium_chat_users" or gauge_type == "active_chat_users":
                user_stats.sort(key=lambda x: x["messageCount"], reverse=True)
            elif gauge_type == "sketch_users":
                user_stats.sort(key=lambda x: x["sketchCount"], reverse=True)
            elif gauge_type == "render_users":
                user_stats.sort(key=lambda x: x["renderCount"], reverse=True)
            
            return user_stats
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {str(e)}")
            raise

    async def _get_total_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get total number of users from Descope"""
        descope_url = os.getenv('DESCOPE_API_URL', 'https://api.descope.com/v1/mgmt/user/search')
        bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
        
        if not bearer_token:
            logger.error("Descope bearer token not found")
            return {"value": 0, "previousValue": 0, "trend": "neutral"}

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

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    descope_url,
                    headers=headers,
                    json=payload,
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('users', [])
                        total_count = len(users)
                        previous_count = int(total_count * 0.9)  # Simulated previous value
                        change_percentage = ((total_count - previous_count) / previous_count * 100) if previous_count > 0 else 0
                        return {
                            "value": total_count,
                            "previousValue": previous_count,
                            "trend": "up" if total_count > previous_count else "down",
                            "changePercentage": round(change_percentage, 2)
                        }
                    else:
                        logger.error(f"Descope API error: {response.status}")
                        return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}
        except Exception as e:
            logger.error(f"Error fetching total users: {str(e)}")
            return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}

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

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = result["aggregations"]["unique_users"]["value"]
            previous_count = int(count * 0.9)  # Simulated previous value
            change_percentage = ((count - previous_count) / previous_count * 100) if previous_count > 0 else 0
            return {
                "value": count,
                "previousValue": previous_count,
                "trend": "up" if count > previous_count else "down",
                "changePercentage": round(change_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting thread users: {str(e)}")
            return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}

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

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = result["aggregations"]["unique_users"]["value"]
            previous_count = int(count * 0.9)  # Simulated previous value
            change_percentage = ((count - previous_count) / previous_count * 100) if previous_count > 0 else 0
            return {
                "value": count,
                "previousValue": previous_count,
                "trend": "up" if count > previous_count else "down",
                "changePercentage": round(change_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting sketch users: {str(e)}")
            return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}

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

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = result["aggregations"]["unique_users"]["value"]
            previous_count = int(count * 0.9)  # Simulated previous value
            change_percentage = ((count - previous_count) / previous_count * 100) if previous_count > 0 else 0
            return {
                "value": count,
                "previousValue": previous_count,
                "trend": "up" if count > previous_count else "down",
                "changePercentage": round(change_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting render users: {str(e)}")
            return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}

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

        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "users": {
                        "terms": {
                            "field": "trace_id.keyword",
                            "size": 10000
                        },
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

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = len(result["aggregations"]["users"]["buckets"])
            previous_count = int(count * 0.9)  # Simulated previous value
            change_percentage = ((count - previous_count) / previous_count * 100) if previous_count > 0 else 0
            return {
                "value": count,
                "previousValue": previous_count,
                "trend": "up" if count > previous_count else "down",
                "changePercentage": round(change_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting medium chat users: {str(e)}")
            return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}

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

        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "users": {
                        "terms": {
                            "field": "trace_id.keyword",
                            "size": 10000
                        },
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

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = len(result["aggregations"]["users"]["buckets"])
            previous_count = int(count * 0.9)  # Simulated previous value
            change_percentage = ((count - previous_count) / previous_count * 100) if previous_count > 0 else 0
            return {
                "value": count,
                "previousValue": previous_count,
                "trend": "up" if count > previous_count else "down",
                "changePercentage": round(change_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting power users: {str(e)}")
            return {"value": 0, "previousValue": 0, "trend": "neutral", "changePercentage": 0}

    async def _get_user_render_counts(self, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Get render counts for each user"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }

        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "renderStart_end"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "users": {
                        "terms": {
                            "field": "trace_id.keyword",
                            "size": 10000
                        }
                    }
                }
            }
        )

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            return {
                bucket["key"]: bucket["doc_count"]
                for bucket in result["aggregations"]["users"]["buckets"]
            }
        except Exception as e:
            logger.error(f"Error getting render counts: {str(e)}")
            return {}

    async def _get_user_message_counts(self, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Get message counts for each user"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }

        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "handleMessageInThread_start"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "users": {
                        "terms": {
                            "field": "trace_id.keyword",
                            "size": 10000
                        }
                    }
                }
            }
        )

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            return {
                bucket["key"]: bucket["doc_count"]
                for bucket in result["aggregations"]["users"]["buckets"]
            }
        except Exception as e:
            logger.error(f"Error getting message counts: {str(e)}")
            return {}

    async def _get_user_sketch_counts(self, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Get sketch counts for each user"""
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }

        query = self.query_builder.build_composite_query(
            must_conditions=[
                {"term": {"event_name.keyword": "uploadSketch_end"}},
                time_filter
            ],
            aggregations={
                "aggs": {
                    "users": {
                        "terms": {
                            "field": "trace_id.keyword",
                            "size": 10000
                        }
                    }
                }
            }
        )

        try:
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            return {
                bucket["key"]: bucket["doc_count"]
                for bucket in result["aggregations"]["users"]["buckets"]
            }
        except Exception as e:
            logger.error(f"Error getting sketch counts: {str(e)}")
            return {}

    async def _get_user_details(self, user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get user details from Descope"""
        descope_url = os.getenv('DESCOPE_API_URL', 'https://api.descope.com/v1/mgmt/user/search')
        bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
        
        if not bearer_token:
            logger.error("Descope bearer token not found")
            return {}

        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "customAttributes": {
                "v2UserId": user_ids
            }
        }

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    descope_url,
                    headers=headers,
                    json=payload,
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('users', [])
                        
                        # Create a mapping of v2UserId to user details
                        user_details = {}
                        for user in users:
                            v2user_id = user.get('customAttributes', {}).get('v2UserId')
                            if v2user_id and v2user_id in user_ids:
                                user_details[v2user_id] = {
                                    'email': user.get('email', ''),
                                    'name': user.get('name', '')
                                }
                        return user_details
                    else:
                        logger.error(f"Descope API error: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching user details: {str(e)}")
            return {}

    def _format_date_os(self, dt: datetime) -> int:
        """Format datetime to OpenSearch timestamp"""
        return int(dt.timestamp() * 1000)

    def _format_date_iso(self, dt: datetime) -> str:
        """Format datetime to ISO string"""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")