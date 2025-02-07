"""
OpenSearch service for querying and aggregating analytics data
"""
import os
import logging
import ssl
import certifi
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from opensearchpy import AsyncOpenSearch, ConnectionError, TransportError
import pytz
from dateutil import tz
from datetime import timezone

logger = logging.getLogger(__name__)

class OpenSearchService:
    def __init__(self):
        self.index = "events-v2"
        self.timestamp_field = "timestamp"
        self.request_timeout = int(os.getenv('MAX_QUERY_TIME', '30'))  # Request timeout in seconds
        self.max_retries = 3
        self.base_delay = 1  # Base delay in seconds

        # Configure OpenSearch client
        self.opensearch_url = os.getenv('OPENSEARCH_URL', 'https://localhost:9200')
        self.opensearch_username = os.getenv('OPENSEARCH_USERNAME')
        self.opensearch_password = os.getenv('OPENSEARCH_PASSWORD')
        
        # Configure SSL context for OpenSearch
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = False  # Disable hostname checking for localhost
        self.ssl_context.verify_mode = ssl.CERT_NONE  # Allow self-signed certificates for local development
        
        # Initialize OpenSearch client
        self.client = AsyncOpenSearch(
            hosts=[self.opensearch_url],
            http_auth=(self.opensearch_username, self.opensearch_password),
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            ssl_context=self.ssl_context
        )

    async def verify_connection(self) -> bool:
        """Verify the connection to OpenSearch and the existence of the index"""
        try:
            # Check if we can connect to OpenSearch
            info = await self.client.info()
            logger.info(f"Successfully connected to OpenSearch cluster: {info['cluster_name']}")

            # Check if the index exists
            index_exists = await self.client.indices.exists(index=self.index)
            if index_exists:
                logger.info(f"Index '{self.index}' exists")
                return True
            else:
                logger.error(f"Index '{self.index}' does not exist")
                return False
        except ConnectionError as e:
            logger.error(f"Failed to connect to OpenSearch: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error verifying OpenSearch connection: {str(e)}")
            return False

    async def _execute_with_retry(self, operation):
        """Execute an OpenSearch operation with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                return await operation()
            except (ConnectionError, TransportError) as e:
                if attempt == self.max_retries - 1:
                    raise e
                delay = self.base_delay * (2**attempt)  # Exponential backoff
                await asyncio.sleep(delay)

    async def search(self, query: Dict[str, Any], size: int = 0) -> Dict[str, Any]:
        """Execute a search query on OpenSearch"""
        logger.debug(f"Executing OpenSearch query: index={self.index}, query={query}, size={size}")
        
        async def execute():
            return await self.client.search(
                index=self.index,
                body=query,
                size=size,
                request_timeout=self.request_timeout
            )

        try:
            result = await self._execute_with_retry(execute)
            logger.debug(f"OpenSearch query result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error executing OpenSearch query: {str(e)}", exc_info=True)
            raise

    async def get_user_counts(self, start_date: datetime, end_date: datetime, event_name: str) -> Dict[str, int]:
        """Get counts of users who performed a specific event"""
        logger.debug(f"Getting user counts for event: {event_name}, start_date: {start_date}, end_date: {end_date}")
        
        # Ensure dates are in UTC
        if start_date.tzinfo is None:
            start_date = start_date.astimezone()
        if end_date.tzinfo is None:
            end_date = end_date.astimezone()
            
        start_utc = start_date.astimezone(pytz.utc)
        end_utc = end_date.astimezone(pytz.utc)
        
        # Convert to milliseconds
        start_ms = int(start_utc.timestamp() * 1000)
        end_ms = int(end_utc.timestamp() * 1000)
        
        logger.debug(f"Converted timestamps - Start UTC: {start_utc.isoformat()}, End UTC: {end_utc.isoformat()}")
        logger.debug(f"Millisecond timestamps - Start: {start_ms}, End: {end_ms}")
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"event_name.keyword": event_name}},
                        {"range": {"timestamp": {"gte": start_ms, "lte": end_ms}}}
                    ]
                }
            },
            "aggs": {
                "users": {
                    "terms": {
                        "field": "trace_id.keyword",
                        "size": 10000
                    }
                }
            }
        }
        
        logger.debug(f"Executing OpenSearch query: index={self.index}, query={query}, size=0")
        
        try:
            response = await self.client.search(
                index=self.index,
                body=query,
                size=0
            )
            logger.debug(f"OpenSearch query result: {response}")
            
            # Extract user counts from aggregation buckets
            user_counts = {
                bucket["key"]: bucket["doc_count"]
                for bucket in response["aggregations"]["users"]["buckets"]
            }
            logger.debug(f"User counts result: {user_counts}")
            return user_counts
            
        except Exception as e:
            logger.error(f"Error executing OpenSearch query: {str(e)}")
            return {}

    async def get_user_events(self, trace_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch user events based on trace_id"""
        logger.debug(f"Getting user events for trace_id: {trace_id}, start_date: {start_date}, end_date: {end_date}")
        time_filter = {
            "range": {
                self.timestamp_field: {
                    "gte": self._format_date_os(start_date),
                    "lte": self._format_date_os(end_date)
                }
            }
        }

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"trace_id.keyword": trace_id}},
                        time_filter
                    ]
                }
            },
            "sort": [{self.timestamp_field: {"order": "desc"}}]
        }

        try:
            result = await self.search(query, size=100)  # Limit to 100 most recent events
            events = [hit["_source"] for hit in result["hits"]["hits"]]
            logger.debug(f"User events result: {events}")
            return events
        except Exception as e:
            logger.error(f"Error fetching user events: {str(e)}", exc_info=True)
            return []

    async def get_producers_count(self, date: Optional[datetime] = None) -> int:
        """Get count of unique producers up to a specific date"""
        logger.info("Starting get_producers_count")
        logger.info(f"Executing producers search query on index: {self.index}")
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"event_name.keyword": "uploadSketch_end"}}
                    ]
                }
            }
        }

        # Add date filter if specified
        if date:
            date_utc = date.astimezone(pytz.utc)
            date_ms = int(date_utc.timestamp() * 1000)
            query["query"]["bool"]["must"].append({
                "range": {
                    "timestamp": {
                        "lte": date_ms
                    }
                }
            })
        
        query["aggs"] = {
            "unique_producers": {
                "cardinality": {
                    "field": "trace_id.keyword"
                }
            }
        }
        
        logger.debug(f"Executing OpenSearch query: index={self.index}, query={query}, size=0")
        
        try:
            response = await self.client.search(
                index=self.index,
                body=query,
                size=0
            )
            logger.debug(f"OpenSearch query result: {response}")
            
            producers_count = response["aggregations"]["unique_producers"]["value"]
            logger.info(f"Found {producers_count} producers")
            return producers_count
            
        except Exception as e:
            logger.error(f"Error executing producers query: {str(e)}")
            return 0

    async def list_event_names(self) -> List[str]:
        """List all event names in OpenSearch"""
        query = {
            "size": 0,
            "aggs": {
                "event_names": {
                    "terms": {
                        "field": "event_name.keyword",
                        "size": 100
                    }
                }
            }
        }
        
        try:
            result = await self.client.search(
                index=self.index,
                body=query
            )
            logger.debug(f"Event names query result: {result}")
            
            buckets = result.get("aggregations", {}).get("event_names", {}).get("buckets", [])
            event_names = [bucket["key"] for bucket in buckets]
            logger.info(f"Found event names: {event_names}")
            return event_names
            
        except Exception as e:
            logger.error(f"Error listing event names: {e}")
            return []

    async def get_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Get metrics from OpenSearch"""
        # Check if date range is before our data starts
        opensearch_start = datetime(2025, 1, 20, tzinfo=timezone.utc)
        if end_date < opensearch_start:
            logger.debug(f"Date range {start_date.isoformat()} to {end_date.isoformat()} is before OpenSearch data starts ({opensearch_start.isoformat()})")
            return {
                "thread_users_count": 0,
                "render_users": 0,
                "producers_count": 0
            }
            
        # Adjust start date if needed
        if start_date < opensearch_start:
            logger.debug(f"Adjusting start date from {start_date.isoformat()} to {opensearch_start.isoformat()}")
            start_date = opensearch_start

        # List all event names first
        event_names = await self.list_event_names()
        logger.info(f"Available event names: {event_names}")
        
        # Get thread users (active users) - try different event names
        thread_users = {}
        thread_event_names = ["handleMessageInThread_start", "threadStart", "thread_start"]
        for event_name in thread_event_names:
            if event_name in event_names:
                users = await self.get_user_counts(event_name, start_date, end_date)
                thread_users.update(users)
        
        # Get producers count - this might come from a specific event or tag
        producers = await self.get_producers_count(end_date)
        
        logger.debug(f"OpenSearch metrics: thread_users={len(thread_users)}, producers={producers}")
        
        return {
            "thread_users_count": len(thread_users),
            "producers_count": producers
        }

    def _format_date_os(self, dt: datetime) -> int:
        """Convert datetime to OpenSearch timestamp (milliseconds)"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to milliseconds since epoch
        timestamp_ms = int(dt.timestamp() * 1000)
        
        # Add debug logging
        logger.debug(f"Converting {dt.isoformat()} to timestamp: {timestamp_ms}")
        
        # Validate timestamp is in reasonable range
        current_time_ms = int(time.time() * 1000)
        if timestamp_ms > current_time_ms:
            logger.warning(f"Generated timestamp {timestamp_ms} is in the future! Using current time instead.")
            timestamp_ms = current_time_ms
            
        return timestamp_ms