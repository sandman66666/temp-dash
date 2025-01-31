"""
AnalyticsService: Core service for fetching and aggregating analytics data
"""
from typing import Dict, Any
import logging
import asyncio
from datetime import datetime, timedelta
from opensearchpy import AsyncOpenSearch
import aioredis
from .cache import analytics_cache

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, opensearch_client: AsyncOpenSearch, redis_client: aioredis.Redis):
        self.opensearch = opensearch_client
        self.redis = redis_client
        self.index = "events-v2"
        self.cache_ttl = timedelta(minutes=5)

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics needed for the dashboard.
        Uses Redis cache with OpenSearch as the source of truth.
        """
        cache_key = "dashboard_metrics"
        
        # Try to get from cache first
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            return cached_data

        try:
            # Get all required metrics concurrently
            descope_users, thread_users, sketch_users, render_users, medium_users, power_users = await asyncio.gather(
                self._get_total_users(),
                self._get_thread_users(),
                self._get_sketch_users(),
                self._get_render_users(),
                self._get_medium_chat_users(),
                self._get_power_users()
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
                }
            }

            # Cache the results
            await self.redis.set(
                cache_key,
                metrics,
                expire=int(self.cache_ttl.total_seconds())
            )

            return metrics

        except Exception as e:
            logger.error(f"Error fetching dashboard metrics: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }

    async def _get_thread_users(self) -> Dict[str, Any]:
        """Get count of users with message threads"""
        query = {
            "aggs": {
                "unique_users": {
                    "cardinality": {
                        "field": "trace_id.keyword"
                    }
                }
            },
            "query": {
                "term": {
                    "event_name.keyword": "handleMessageInThread_start"
                }
            }
        }
        
        result = await self.opensearch.search(
            index=self.index,
            body=query,
            size=0
        )

        count = result["aggregations"]["unique_users"]["value"]
        
        return {
            "value": count,
            "label": "Thread Users",
            "description": "Users who have started at least one message thread"
        }

    async def _get_sketch_users(self) -> Dict[str, Any]:
        """Get count of users who have uploaded sketches"""
        query = {
            "aggs": {
                "unique_users": {
                    "cardinality": {
                        "field": "trace_id.keyword"
                    }
                }
            },
            "query": {
                "term": {
                    "event_name.keyword": "uploadSketch_end"
                }
            }
        }
        
        result = await self.opensearch.search(
            index=self.index,
            body=query,
            size=0
        )

        count = result["aggregations"]["unique_users"]["value"]
        
        return {
            "value": count,
            "label": "Sketch Users",
            "description": "Users who have uploaded at least one sketch"
        }

    async def _get_render_users(self) -> Dict[str, Any]:
        """Get count of users who have completed renders"""
        query = {
            "aggs": {
                "unique_users": {
                    "cardinality": {
                        "field": "trace_id.keyword"
                    }
                }
            },
            "query": {
                "term": {
                    "event_name.keyword": "renderStart_end"
                }
            }
        }
        
        result = await self.opensearch.search(
            index=self.index,
            body=query,
            size=0
        )

        count = result["aggregations"]["unique_users"]["value"]
        
        return {
            "value": count,
            "label": "Render Users",
            "description": "Users who have completed at least one render"
        }

    async def _get_medium_chat_users(self) -> Dict[str, Any]:
        """Get users with 5-20 message threads"""
        query = {
            "aggs": {
                "thread_count": {
                    "terms": {
                        "field": "trace_id.keyword",
                        "size": 10000
                    },
                    "aggs": {
                        "thread_filter": {
                            "bucket_selector": {
                                "buckets_path": {
                                    "count": "_count"
                                },
                                "script": "params.count >= 5 && params.count <= 20"
                            }
                        }
                    }
                }
            },
            "query": {
                "term": {
                    "event_name.keyword": "handleMessageInThread_start"
                }
            }
        }
        
        result = await self.opensearch.search(
            index=self.index,
            body=query,
            size=0
        )

        count = len(result["aggregations"]["thread_count"]["buckets"])
        
        return {
            "value": count,
            "label": "Medium Activity Users",
            "description": "Users with 5-20 message threads"
        }

    async def _get_power_users(self) -> Dict[str, Any]:
        """Get users with more than 20 message threads"""
        query = {
            "aggs": {
                "thread_count": {
                    "terms": {
                        "field": "trace_id.keyword",
                        "size": 10000
                    },
                    "aggs": {
                        "thread_filter": {
                            "bucket_selector": {
                                "buckets_path": {
                                    "count": "_count"
                                },
                                "script": "params.count > 20"
                            }
                        }
                    }
                }
            },
            "query": {
                "term": {
                    "event_name.keyword": "handleMessageInThread_start"
                }
            }
        }
        
        result = await self.opensearch.search(
            index=self.index,
            body=query,
            size=0
        )

        count = len(result["aggregations"]["thread_count"]["buckets"])
        
        return {
            "value": count,
            "label": "Power Users",
            "description": "Users with more than 20 message threads"
        }

    async def _get_total_users(self) -> Dict[str, Any]:
        """Get total number of users from Descope"""
        # Implement Descope users count here
        # For now returning mock data
        return {
            "value": 1000,  # Replace with actual Descope API call
            "label": "Total Users",
            "description": "Total number of registered users"
        }