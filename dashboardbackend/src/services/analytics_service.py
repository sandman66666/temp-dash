"""
AnalyticsService: Core service for fetching and aggregating analytics data
"""
from typing import Dict, Any, List, Optional
import logging
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
            # Get current period metrics from OpenSearch
            message_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "handleMessageInThread_start")
            render_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "renderStart_end")
            sketch_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "uploadSketch_end")

            # Calculate user segments
            active_users = len([u for u in message_counts.values() if u > 0])
            power_users = len([u for u in message_counts.values() if u > 20])
            moderate_users = len([u for u in message_counts.values() if 5 <= u <= 20])
            producers = len([u for u in render_counts.values() if u > 0])
            producers_attempting = len([u for u in sketch_counts.values() if u > 0])

            # Get total users from Descope
            total_users = await self.descope_service.get_total_users()
            if total_users == 0:
                # Use unique users from OpenSearch as fallback
                all_users = set(message_counts.keys()) | set(render_counts.keys()) | set(sketch_counts.keys())
                total_users = len(all_users)
                logger.info(f"Using OpenSearch unique users as fallback for total users: {total_users}")

            # Calculate previous period dates
            days_diff = (end_date - start_date).days
            prev_end_date = start_date
            prev_start_date = prev_end_date - timedelta(days=days_diff)

            # Get previous period metrics from OpenSearch
            prev_message_counts = await self.opensearch_service.get_user_counts(prev_start_date, prev_end_date, "handleMessageInThread_start")
            prev_render_counts = await self.opensearch_service.get_user_counts(prev_start_date, prev_end_date, "renderStart_end")
            prev_sketch_counts = await self.opensearch_service.get_user_counts(prev_start_date, prev_end_date, "uploadSketch_end")

            # Calculate previous period metrics
            active_users_prev = len([u for u in prev_message_counts.values() if u > 0])
            power_users_prev = len([u for u in prev_message_counts.values() if u > 20])
            moderate_users_prev = len([u for u in prev_message_counts.values() if 5 <= u <= 20])
            producers_prev = len([u for u in prev_render_counts.values() if u > 0])
            producers_attempting_prev = len([u for u in prev_sketch_counts.values() if u > 0])

            # Format metrics for frontend
            current_date = datetime.now(timezone.utc)
            previous_date = current_date - timedelta(days=30)  # Use 30 days ago for previous period
            
            # Get current unfiltered totals
            current_date = datetime.now(timezone.utc)
            one_year_ago = current_date - timedelta(days=365)
            
            # Get unfiltered active users (all time)
            unfiltered_active_counts = await self.opensearch_service.get_user_counts(
                one_year_ago,
                current_date,
                "handleMessageInThread_start"
            )
            unfiltered_active_users = len([u for u in unfiltered_active_counts.values() if u > 0])

            # Get unfiltered producers (all time)
            unfiltered_producer_counts = await self.opensearch_service.get_user_counts(
                one_year_ago,
                current_date,
                "renderStart_end"
            )
            unfiltered_producers = len([u for u in unfiltered_producer_counts.values() if u > 0])

            # V1 historical numbers
            v1_total_users = 55000
            v1_active_users = 30000
            v1_producers = 15000

            # Add historical total metrics
            historical_total_metrics = [
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
                        "value": v1_active_users + unfiltered_active_users,
                        "trend": "neutral"
                    }
                },
                {
                    "id": "historical_producers",
                    "name": "All Time Producers",
                    "description": "Total producers including V1",
                    "category": "historical",
                    "interval": "all_time",
                    "data": {
                        "value": v1_producers + unfiltered_producers,
                        "trend": "neutral"
                    }
                }
            ]

            formatted_metrics = [
                {
                    "id": "total_users",
                    "name": "Total Users",
                    "description": "Total number of registered users",
                    "category": "user",
                    "interval": "daily",
                    "data": {
                        "value": total_users,
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
                        "trend": "neutral",
                        "changePercentage": 0,
                        "historical": [
                            {"date": previous_date.isoformat(), "value": active_users_prev},
                            {"date": current_date.isoformat(), "value": active_users}
                        ]
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
                        "trend": "neutral",
                        "changePercentage": 0,
                        "historical": [
                            {"date": previous_date.isoformat(), "value": power_users_prev},
                            {"date": current_date.isoformat(), "value": power_users}
                        ]
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
                        "trend": "neutral",
                        "changePercentage": 0,
                        "historical": [
                            {"date": previous_date.isoformat(), "value": moderate_users_prev},
                            {"date": current_date.isoformat(), "value": moderate_users}
                        ]
                    }
                },
                {
                    "id": "producers",
                    "name": "Producers",
                    "description": "Users who have completed at least one render",
                    "category": "engagement",
                    "interval": "daily",
                    "data": {
                        "value": producers,
                        "previousValue": producers_prev,
                        "trend": "neutral",
                        "changePercentage": 0,
                        "historical": [
                            {"date": previous_date.isoformat(), "value": producers_prev},
                            {"date": current_date.isoformat(), "value": producers}
                        ]
                    }
                },
                {
                    "id": "producers_attempting",
                    "name": "Producers Attempting",
                    "description": "Users who have uploaded at least one sketch",
                    "category": "engagement",
                    "interval": "daily",
                    "data": {
                        "value": producers_attempting,
                        "previousValue": producers_attempting_prev,
                        "trend": "neutral",
                        "changePercentage": 0,
                        "historical": [
                            {"date": previous_date.isoformat(), "value": producers_attempting_prev},
                            {"date": current_date.isoformat(), "value": producers_attempting}
                        ]
                    }
                }
            ]

            formatted_metrics.extend(historical_total_metrics)

            logger.info(f"Final dashboard metrics: {formatted_metrics}")
            return formatted_metrics

        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {str(e)}", exc_info=True)
            raise

    async def get_user_statistics(self, start_date: datetime, end_date: datetime, gauge_type: str) -> List[Dict[str, Any]]:
        """Get user statistics including message and sketch counts"""
        try:
            # Get all user activity counts
            message_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "handleMessageInThread_start")
            sketch_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "uploadSketch_end")
            render_counts = await self.opensearch_service.get_user_counts(start_date, end_date, "renderStart_end")

            # Get user details from Descope
            all_user_ids = set(message_counts.keys()) | set(sketch_counts.keys()) | set(render_counts.keys())
            user_details = await self.descope_service.get_user_details(list(all_user_ids))

            # Filter users based on gauge type
            filtered_users = []
            for user_id in all_user_ids:
                message_count = message_counts.get(user_id, 0)
                sketch_count = sketch_counts.get(user_id, 0)
                render_count = render_counts.get(user_id, 0)

                # Apply filters based on gauge type
                include_user = False
                if gauge_type == 'active_users' and message_count > 0:
                    include_user = True
                elif gauge_type == 'power_users' and message_count > 20:
                    include_user = True
                elif gauge_type == 'moderate_users' and 5 <= message_count <= 20:
                    include_user = True
                elif gauge_type == 'producers' and render_count > 0:
                    include_user = True
                elif gauge_type == 'producers_attempting' and sketch_count > 0:
                    include_user = True

                if include_user:
                    user_detail = user_details.get(user_id, {})
                    filtered_users.append({
                        'trace_id': user_id,
                        'email': user_detail.get('email', ''),
                        'name': user_detail.get('name', ''),
                        'messageCount': message_count,
                        'sketchCount': sketch_count,
                        'renderCount': render_count
                    })

            return filtered_users

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
            "thread_users_count": 0,
            "render_users": 0,
            "producers_count": 0,
            "daily_total_users": 0,
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
                "thread_users_count": historical_metrics.get("active_users", 0),  # Active users maps to thread users
                "producers_count": historical_metrics.get("producers", 0),
                "daily_total_users": historical_metrics.get("daily_total_users", 0),
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
            total_users = await self.descope_service.get_total_users()
            metrics["total_users"] = max(metrics["total_users"], total_users)
        
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
                    "interval": "daily",
                    "data": {
                        "value": metrics["total_users"],  # Raw total
                        "previousValue": 0,
                        "trend": "up",
                        "changePercentage": 0,
                        "daily_average": metrics["daily_total_users"]  # Daily average
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