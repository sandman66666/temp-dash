"""
AnalyticsService: Core service for fetching and aggregating analytics data
"""
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime, timedelta
import os
from src.services.metrics_service import AnalyticsMetricsService
from src.services.descope_service import DescopeService
from src.services.opensearch_service import OpenSearchService
from src.services.historical_data_service import HistoricalDataService
from src.services.caching_service import CachingService
from src.utils.query_builder import OpenSearchQueryBuilder
from datetime import timezone

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, caching_service: CachingService, opensearch_service: OpenSearchService, query_builder: OpenSearchQueryBuilder, descope_service: DescopeService):
        self.caching_service = caching_service
        self.disable_cache = os.getenv('DISABLE_CACHE', 'false').lower() == 'true'
        self.opensearch_service = opensearch_service
        self.descope_service = descope_service
        self.historical_data_service = HistoricalDataService()
        self.analytics_metrics = AnalyticsMetricsService(
            self.opensearch_service,
            self.caching_service,
            query_builder,
            os.getenv('OPENSEARCH_INDEX', 'your_index_name'),
            os.getenv('OPENSEARCH_TIMESTAMP_FIELD', 'timestamp'),
            int(os.getenv('OPENSEARCH_REQUEST_TIMEOUT', '30')),
            self.descope_service
        )

    async def get_dashboard_metrics(self, start_date: datetime, end_date: datetime, include_v1: bool = False) -> Dict[str, Any]:
        """Get all dashboard metrics for the given time period."""
        try:
            # Create cache key including date range
            cache_key = f"dashboard_metrics:{start_date.isoformat()}:{end_date.isoformat()}"
            
            # Try to get from cache first
            if not self.disable_cache:
                cached_data = await self.caching_service.get(cache_key)
                if cached_data:
                    logger.info("Returning cached dashboard metrics")
                    return cached_data

            # Get current period metrics from OpenSearch
            message_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "handleMessageInThread_start")
            
            # Get render counts using the correct event name
            render_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "renderStart_end")
            logger.info(f"Render counts: {len(render_counts)}")
            
            sketch_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "uploadSketch_end")

            # Log counts for debugging
            logger.info(f"Message counts: {len(message_counts)}")
            logger.info(f"Render counts: {len(render_counts)}")
            logger.info(f"Sketch counts: {len(sketch_counts)}")

            # Calculate user segments
            active_users = len([u for u in message_counts.values() if u > 0])
            power_users = len([u for u in message_counts.values() if u > 20])
            moderate_users = len([u for u in message_counts.values() if 5 <= u <= 20])
            producers = len([u for u in render_counts.values() if u > 0])
            productions = sum(render_counts.values())  # Total number of renders

            logger.info(f"Active users: {active_users}")
            logger.info(f"Producers: {producers}")
            logger.info(f"Productions: {productions}")

            # Get total users from Descope for the period
            logger.info(f"Getting total users at {end_date}")
            total_users = await self.descope_service.get_total_users(end_date)  # Filter by end_date
            logger.info(f"Total users at end date: {total_users}")
            
            # Calculate new users based on users created in the period
            new_users = await self.descope_service.get_new_users_in_period(start_date, end_date)
            logger.info(f"Total users: {total_users}")
            logger.info(f"New users in period: {new_users}")

            # Calculate previous period dates
            days_diff = (end_date - start_date).days
            prev_end_date = start_date
            prev_start_date = prev_end_date - timedelta(days=days_diff)

            # Get previous period metrics from OpenSearch
            prev_message_counts = await self.opensearch_service.get_user_counts(prev_start_date, prev_end_date, "handleMessageInThread_start")
            prev_render_counts = await self.opensearch_service.get_user_counts(prev_start_date, prev_end_date, "renderStart_end")
            logger.info(f"Previous render counts: {len(prev_render_counts)}")

            # Calculate previous period metrics
            active_users_prev = len([u for u in prev_message_counts.values() if u > 0])
            power_users_prev = len([u for u in prev_message_counts.values() if u > 20])
            moderate_users_prev = len([u for u in prev_message_counts.values() if 5 <= u <= 20])
            producers_prev = len([u for u in prev_render_counts.values() if u > 0])
            productions_prev = sum(prev_render_counts.values())

            # Get all-time metrics for historical totals
            current_date = datetime.now(timezone.utc)
            one_year_ago = current_date - timedelta(days=365)
            
            # Get all-time active users
            all_time_message_counts = await self.opensearch_service.get_user_counts(
                one_year_ago,
                current_date,
                "handleMessageInThread_start"
            )
            all_time_active_users = len([u for u in all_time_message_counts.values() if u > 0])

            # Get all-time productions and producers
            all_time_render_counts = await self.opensearch_service.get_user_counts(one_year_ago, current_date, "renderStart_end")
            logger.info(f"All-time render counts: {len(all_time_render_counts)}")
            all_time_producers = len([u for u in all_time_render_counts.values() if u > 0])
            all_time_productions = sum(all_time_render_counts.values())

            # Baseline numbers
            v1_total_users = 55000
            v1_active_users = 16560
            v1_productions = 30251

            # Format metrics
            formatted_metrics = [
                # Historical metrics (not affected by date range)
                {
                    "id": "historical_total_users",
                    "name": "All Time Total Users",
                    "description": "Total users including V1",
                    "category": "historical",
                    "interval": "all_time",
                    "data": {
                        "value": v1_total_users + total_users,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "historical_active_users",
                    "name": "All Time Active Users",
                    "description": "Total active users including V1",
                    "category": "historical",
                    "interval": "all_time",
                    "data": {
                        "value": v1_active_users + all_time_active_users,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "historical_productions",
                    "name": "Productions",
                    "description": "Total successful productions including V1",
                    "category": "historical",
                    "interval": "all_time",
                    "data": {
                        "value": v1_productions + all_time_productions,
                        "trend": "neutral"
                    }
                },
                # Current period metrics (affected by date range)
                {
                    "id": "total_users_count",
                    "name": "Total Users",
                    "description": "Total number of users registered as of this period",
                    "category": "user",
                    "interval": "cumulative",
                    "data": {
                        "value": total_users,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "new_users",
                    "name": "New Users",
                    "description": "Users who registered during this period",
                    "category": "user",
                    "interval": "daily",
                    "data": {
                        "value": new_users,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "active_users",
                    "name": "Active Users",
                    "description": "Users who have started at least one message thread",
                    "category": "user",
                    "interval": "daily",
                    "data": {
                        "value": active_users,
                        "previousValue": active_users_prev,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "producers",
                    "name": "Producers",
                    "description": "Users who have completed at least one render",
                    "category": "user",
                    "interval": "daily",
                    "data": {
                        "value": producers,
                        "previousValue": producers_prev,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "power_users",
                    "name": "Power Users",
                    "description": "Users with more than 20 message threads",
                    "category": "engagement",
                    "interval": "daily",
                    "data": {
                        "value": power_users,
                        "previousValue": power_users_prev,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "moderate_users",
                    "name": "Moderate Users",
                    "description": "Users with 5-20 message threads",
                    "category": "engagement",
                    "interval": "daily",
                    "data": {
                        "value": moderate_users,
                        "previousValue": moderate_users_prev,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "productions",
                    "name": "Productions",
                    "description": "Total number of completed renders",
                    "category": "performance",
                    "interval": "daily",
                    "data": {
                        "value": productions,
                        "previousValue": productions_prev,
                        "trend": "neutral"
                    }
                }
            ]

            # Cache the results with the date range
            if not self.disable_cache:
                await self.caching_service.set(cache_key, formatted_metrics, ttl=timedelta(minutes=5))

            return formatted_metrics

        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}", exc_info=True)
            raise

    async def get_user_statistics(self, start_date: datetime, end_date: datetime, gauge_type: str) -> List[Dict[str, Any]]:
        """Get user statistics based on the gauge type."""
        try:
            logger.info(f"Getting user statistics for gauge type: {gauge_type}")

            # Get user counts for different event types
            message_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "handleMessageInThread_start")
            render_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "renderStart_end")
            sketch_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "uploadSketch_end")
            
            # Filter users based on gauge type
            filtered_users = set()
            if gauge_type == 'power_users':
                filtered_users = {user_id for user_id, count in message_counts.items() if count >= 20}
            elif gauge_type == 'moderate_users':
                filtered_users = {user_id for user_id, count in message_counts.items() if 5 <= count < 20}
            elif gauge_type == 'producers':
                filtered_users = {user_id for user_id, count in render_counts.items() if count > 0}
            elif gauge_type == 'active_users':
                filtered_users = {user_id for user_id, count in message_counts.items() if count > 0}
            else:
                filtered_users = set(message_counts.keys()) | set(render_counts.keys()) | set(sketch_counts.keys())

            # Log the number of filtered users and their trace_ids
            logger.info(f"Found {len(filtered_users)} users matching gauge type: {gauge_type}")
            logger.debug(f"Filtered users from OpenSearch: {filtered_users}")

            # Get user details from OpenSearch events
            user_details = {}
            for trace_id in filtered_users:
                # Query OpenSearch for events with this trace_id
                query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"trace_id.keyword": trace_id}}
                            ]
                        }
                    }
                }
                events = await self.opensearch_service.search(query, size=1)
                
                if events and len(events.get('hits', {}).get('hits', [])) > 0:
                    event = events['hits']['hits'][0]['_source']
                    headers = event.get('event_data', {}).get('headers', {})
                    auth_header = headers.get('authorization', '')
                    
                    if auth_header and auth_header.startswith('Bearer '):
                        # Extract the JWT token
                        token = auth_header.split(' ')[1]
                        try:
                            # Get the payload part of the JWT (second part)
                            payload = token.split('.')[1]
                            # Add padding if needed
                            padding = 4 - (len(payload) % 4)
                            if padding != 4:
                                payload += '=' * padding
                            
                            # Decode base64
                            import base64
                            import json
                            decoded = base64.b64decode(payload)
                            jwt_data = json.loads(decoded)
                            
                            # Get user details from JWT
                            user_details[trace_id] = {
                                'email': jwt_data.get('email', ''),
                                'name': jwt_data.get('displayName', ''),
                                'createdTime': ''  # We don't have this in the JWT
                            }
                            logger.debug(f"Got user details for {trace_id} from JWT: {user_details[trace_id]}")
                        except Exception as e:
                            logger.error(f"Error decoding JWT for trace_id {trace_id}: {e}")
                else:
                    logger.warning(f"No events found for trace_id: {trace_id}")

            # Format user statistics
            user_stats = []
            for trace_id in filtered_users:
                details = user_details.get(trace_id, {})
                
                if details:
                    logger.debug(f"Found user details for trace_id {trace_id}: {json.dumps(details)}")
                else:
                    logger.warning(f"No user details found for trace_id: {trace_id}")

                stats = {
                    'id': trace_id,
                    'userId': trace_id,
                    'email': details.get('email', ''),
                    'name': details.get('name', ''),
                    'createdTime': details.get('createdTime', ''),
                    'messageCount': message_counts.get(trace_id, 0),
                    'sketchCount': sketch_counts.get(trace_id, 0),
                    'renderCount': render_counts.get(trace_id, 0)
                }
                user_stats.append(stats)

            # Log the final list we're returning
            logger.debug("Final user_stats list:")
            for stat in user_stats:
                logger.debug(f"User stat: {json.dumps(stat)}")

            # Sort users by message count in descending order
            user_stats.sort(key=lambda x: x['messageCount'], reverse=True)
            
            logger.info(f"Returning {len(user_stats)} user statistics records")
            return user_stats

        except Exception as e:
            logger.error(f"Error getting user statistics: {str(e)}", exc_info=True)
            return []

    async def get_user_events(self, trace_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch user events based on trace_id"""
        return await self.opensearch_service.get_user_events(trace_id, start_date, end_date)

    async def merge_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Merge metrics from all sources"""
        # Define the data transition points
        historical_end = datetime(2025, 1, 26, tzinfo=timezone.utc)  # Historical data ends Jan 26th
        opensearch_start = datetime(2025, 1, 20, tzinfo=timezone.utc)  # OpenSearch data starts Jan 20th
        
        self.logger.debug(f"Date range: {start_date.isoformat()} to {end_date.isoformat()}")
        self.logger.debug(f"Historical end: {historical_end.isoformat()}")
        self.logger.debug(f"OpenSearch start: {opensearch_start.isoformat()}")
        
        metrics = {
            "total_users": 0,
            "new_users": 0,
            "thread_users_count": 0,
            "render_users": 0,
            "producers_count": 0,
            "daily_total_users": 0,
            "daily_new_users": 0,
            "daily_thread_users": 0,
            "daily_render_users": 0,
            "daily_producers": 0
        }
        
        # Get historical metrics if date range includes Oct-Jan 26th
        if start_date <= historical_end:
            historical_metrics = await self.historical_data_service.get_v1_metrics(
                start_date,
                min(end_date, historical_end),
                include_v1=True
            )
            self.logger.debug(f"Historical metrics: {historical_metrics}")
            
            # Update metrics with historical data
            metrics.update({
                "total_users": historical_metrics.get("total_users", 0),
                "new_users": historical_metrics.get("new_users", 0),
                "thread_users_count": historical_metrics.get("active_users", 0),  # Active users maps to thread users
                "producers_count": historical_metrics.get("producers", 0),
                "daily_total_users": historical_metrics.get("daily_total_users", 0),
                "daily_new_users": historical_metrics.get("daily_new_users", 0),
                "daily_thread_users": historical_metrics.get("daily_active_users", 0),
                "daily_producers": historical_metrics.get("daily_producers", 0)
            })
        
        # Get OpenSearch metrics if date range includes Jan 20th onwards
        if end_date >= opensearch_start:
            os_metrics = await self.opensearch_service.get_metrics(
                max(start_date, opensearch_start),
                end_date
            )
            self.logger.debug(f"OpenSearch metrics: {os_metrics}")
            
            # If we're in the overlap period (Jan 20-26), merge the metrics
            if start_date <= historical_end and end_date >= opensearch_start:
                overlap_days = (min(end_date, historical_end) - opensearch_start).days + 1
                total_days = (end_date - start_date).days + 1
                
                # Weight the metrics based on the overlap period
                historical_weight = (historical_end - start_date).days + 1
                opensearch_weight = (end_date - opensearch_start).days + 1
                total_weight = historical_weight + opensearch_weight
                
                self.logger.debug(f"Overlap period - historical days: {historical_weight}, opensearch days: {opensearch_weight}")
                
                # Merge metrics with weighted averages for the overlap period
                metrics.update({
                    "thread_users_count": max(metrics["thread_users_count"], os_metrics["thread_users_count"]),
                    "producers_count": max(metrics["producers_count"], os_metrics["producers_count"]),
                    "daily_thread_users": int((metrics["daily_thread_users"] * historical_weight + 
                                            (os_metrics["thread_users_count"] / opensearch_weight) * opensearch_weight) / total_weight),
                    "daily_producers": int((metrics["daily_producers"] * historical_weight + 
                                        (os_metrics["producers_count"] / opensearch_weight) * opensearch_weight) / total_weight)
                })
            
            # If we're only in the OpenSearch period (after Jan 26th), use OpenSearch metrics
            elif start_date > historical_end:
                days_in_range = (end_date - start_date).days + 1
                metrics.update({
                    "thread_users_count": os_metrics["thread_users_count"],
                    "producers_count": os_metrics["producers_count"],
                    "daily_thread_users": int(os_metrics["thread_users_count"] / days_in_range),
                    "daily_producers": int(os_metrics["producers_count"] / days_in_range)
                })
        
        # Get current total users from Descope for the most up-to-date count
        if end_date >= datetime.now(timezone.utc) - timedelta(days=1):
            total_users = await self.descope_service.get_total_users(end_date)  # Filter by end_date
            metrics["total_users"] = total_users  # Just use the filtered total
            
            # Get new users in the period
            new_users = await self.descope_service.get_new_users_in_period(start_date, end_date)
            metrics["new_users"] = new_users
        
        self.logger.debug(f"Final merged metrics: {metrics}")
        return metrics

    async def get_metrics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get all metrics for the dashboard"""
        # If no dates provided, default to October 2024
        if start_date is None:
            start_date = datetime(2024, 10, 1, tzinfo=timezone.utc)
        if end_date is None:
            end_date = datetime(2024, 11, 1, tzinfo=timezone.utc)

        # Ensure dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        self.logger.debug(f"Getting metrics for date range: {start_date.isoformat()} to {end_date.isoformat()}")

        # Get raw metrics and daily averages
        metrics = await self.merge_metrics(start_date, end_date)
        self.logger.debug(f"Final metrics: {metrics}")

        # Build response with both raw and daily values
        response = {
            "metrics": [
                {
                    "id": "descope_users",
                    "name": "Total Users",
                    "description": "Total number of registered users",
                    "category": "user",
                    "interval": "cumulative",
                    "data": {
                        "value": metrics["total_users"],  # Raw total
                        "previousValue": 0,
                        "trend": "up",
                        "changePercentage": 0,
                        "daily_average": metrics["daily_total_users"]  # Daily average
                    }
                },
                {
                    "id": "new_users",
                    "name": "New Users",
                    "description": "Users who registered during this period",
                    "category": "user",
                    "interval": "daily",
                    "data": {
                        "value": metrics["new_users"],  # Raw total
                        "previousValue": 0,
                        "trend": "up",
                        "changePercentage": 0,
                        "daily_average": metrics["daily_new_users"]  # Daily average
                    }
                },
                {
                    "id": "thread_users",
                    "name": "Thread Users",
                    "description": "Users who have started at least one message thread",
                    "category": "engagement",
                    "interval": "daily",
                    "data": {
                        "value": metrics["thread_users_count"],  # Raw total
                        "previousValue": 0,
                        "trend": "up",
                        "changePercentage": 0,
                        "daily_average": metrics["daily_thread_users"]  # Daily average
                    }
                },
                {
                    "id": "render_users",
                    "name": "Render Users",
                    "description": "Users who have completed at least one render",
                    "category": "performance",
                    "interval": "daily",
                    "data": {
                        "value": metrics["render_users"],  # Raw total
                        "previousValue": 0,
                        "trend": "neutral",
                        "changePercentage": 0,
                        "daily_average": metrics["daily_render_users"]  # Daily average
                    }
                },
                {
                    "id": "producers",
                    "name": "Producers",
                    "description": "Total number of producers",
                    "category": "user",
                    "interval": "daily",
                    "data": {
                        "value": metrics["producers_count"],  # Raw total
                        "previousValue": 0,
                        "trend": "up",
                        "changePercentage": 0,
                        "daily_average": metrics["daily_producers"]  # Daily average
                    }
                }
            ],
            "timeRange": {
                "start": self._format_date_iso(start_date),
                "end": self._format_date_iso(end_date)
            }
        }

        return response

    def _format_date_iso(self, dt: datetime) -> str:
        """Format datetime to UTC ISO string"""
        if dt.tzinfo is None:
            dt = dt.astimezone()
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")