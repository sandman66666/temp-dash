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
from src.utils.query_builder import OpenSearchQueryBuilder

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

    def _format_metric(self, id: str, name: str, description: str, value: int, category: str = 'user', previous_value: int = None) -> Dict[str, Any]:
        """Format metric data according to frontend requirements"""
        metric_value = {
            "value": value,
            "previousValue": previous_value if previous_value is not None else value
        }
        
        # Calculate trend if previous value exists
        if previous_value is not None and previous_value > 0:
            change = ((value - previous_value) / previous_value) * 100
            metric_value["changePercentage"] = round(change, 2)
            metric_value["trend"] = "up" if change > 0 else "down" if change < 0 else "neutral"

        return {
            "id": id,
            "name": name,
            "description": description,
            "category": category,
            "data": metric_value,
            "interval": "daily"  # Default to daily interval
        }

    async def _execute_with_retry(self, operation):
        """Execute an OpenSearch operation with exponential backoff retry."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Executing operation, attempt {attempt + 1}/{self.max_retries}")
                return await operation()
            except ConnectionError as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    logger.error(f"Connection failed after {self.max_retries} attempts: {str(e)}")
                    raise
                delay = self.base_delay * (2**attempt)  # Exponential backoff
                logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {delay} seconds: {str(e)}")
                await asyncio.sleep(delay)
            except TransportError as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    logger.error(f"Transport error after {self.max_retries} attempts: {str(e)}")
                    raise
                delay = self.base_delay * (2**attempt)
                logger.warning(f"Transport error on attempt {attempt + 1}, retrying in {delay} seconds: {str(e)}")
                await asyncio.sleep(delay)
            except (NotFoundError, RequestError) as e:
                logger.error(f"OpenSearch error occurred: {str(e)}")
                raise
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}", exc_info=True)
                if attempt == self.max_retries - 1:
                    raise

        if last_error:
            raise last_error

    def _format_date_os(self, dt: datetime) -> int:
        """Format the datetime to epoch milliseconds (for OpenSearch queries)."""
        epoch_ms = int(dt.timestamp() * 1000)
        logger.debug("Formatted %s to epoch ms: %s", dt, epoch_ms)
        return epoch_ms

    def _format_date_iso(self, dt: datetime) -> str:
        """Format the datetime to an ISO string (for caching and external APIs)."""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_dashboard_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get all metrics needed for the dashboard."""
        cache_key = f"dashboard_metrics_{self._format_date_iso(start_date)}_{self._format_date_iso(end_date)}"
        
        if not self.disable_cache:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    logger.debug("Returning cached metrics for key: %s", cache_key)
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis cache retrieval failed: {str(e)}")
        else:
            logger.debug("Caching is disabled. Bypassing Redis cache.")

        try:
            # Get all metrics
            results = await asyncio.gather(
                self._get_total_users(start_date, end_date),
                self._get_thread_users(start_date, end_date),
                self._get_render_users(start_date, end_date),
                self._get_power_users(start_date, end_date),
                self._get_medium_chat_users(start_date, end_date),
                self._get_sketch_users(start_date, end_date),
                return_exceptions=True
            )

            # Format metrics according to frontend requirements
            metrics: List[Dict[str, Any]] = []
            metric_configs = [
                ('descope_users', 'Total Users', 'Total number of registered users'),
                ('thread_users', 'Active Users', 'Users who have started at least one message thread'),
                ('render_users', 'Producers', 'Users who have completed at least one render'),
                ('active_chat_users', 'Power Users', 'Users with more than 20 message threads'),
                ('medium_chat_users', 'Moderate Users', 'Users with 5-20 message threads'),
                ('sketch_users', 'Producers Attempting', 'Users who have uploaded at least one sketch')
            ]

            for i, (metric_id, name, description) in enumerate(metric_configs):
                result = results[i]
                if isinstance(result, Exception):
                    logger.error(f"Error fetching metric {metric_id}: {str(result)}")
                    metrics.append(self._format_metric(
                        metric_id,
                        name,
                        f"Error: {str(result)}",
                        0
                    ))
                else:
                    metrics.append(self._format_metric(
                        metric_id,
                        name,
                        description,
                        result.get('value', 0),
                        'user',
                        result.get('previousValue')
                    ))

            response = {
                "status": "success",
                "metrics": metrics,
                "timeRange": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

            if not self.disable_cache:
                try:
                    await self.redis.set(
                        cache_key,
                        json.dumps(response),
                        ex=int(self.cache_ttl.total_seconds())
                    )
                    logger.debug("Cached metrics with key: %s", cache_key)
                except Exception as e:
                    logger.warning(f"Redis cache storage failed: {str(e)}")

            return response

        except Exception as e:
            logger.error("Error fetching dashboard metrics: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timeRange": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
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

        async def execute():
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = result["aggregations"]["unique_users"]["value"]
            logger.debug("Thread Users count: %s", count)
            return {
                "value": count,
                "label": "Active Users",
                "description": "Users who have started at least one message thread"
            }

        return await self._execute_with_retry(execute)

    async def _get_total_users(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get total number of users from Descope with time filter"""
        import aiohttp

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

        try:
            conn = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.post(descope_url, headers=headers, json=payload, timeout=self.request_timeout) as response:
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

        async def execute():
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = result["aggregations"]["unique_users"]["value"]
            logger.debug("Sketch Users count: %s", count)
            return {
                "value": count,
                "label": "Producers Attempting",
                "description": "Users who have uploaded at least one sketch"
            }

        return await self._execute_with_retry(execute)

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

        async def execute():
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = result["aggregations"]["unique_users"]["value"]
            logger.debug("Render Users count: %s", count)
            return {
                "value": count,
                "label": "Producers",
                "description": "Users who have completed at least one render"
            }

        return await self._execute_with_retry(execute)

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

        async def execute():
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = len(result["aggregations"]["thread_count"]["buckets"])
            logger.debug("Medium Chat Users count: %s", count)
            return {
                "value": count,
                "label": "Moderate Users",
                "description": "Users with 5-20 message threads"
            }

        return await self._execute_with_retry(execute)

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

        async def execute():
            result = await self.opensearch.search(
                index=self.index,
                body=query,
                size=0,
                request_timeout=self.request_timeout
            )
            count = len(result["aggregations"]["thread_count"]["buckets"])
            logger.debug("Power Users count: %s", count)
            return {
                "value": count,
                "label": "Power Users",
                "description": "Users with more than 20 message threads"
            }

        return await self._execute_with_retry(execute)