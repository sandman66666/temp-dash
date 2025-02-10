"""
Service for proactively warming up cache with dashboard data
"""
import logging
from datetime import datetime, timedelta, timezone, date
from calendar import monthrange
from typing import List, Dict, Any
import asyncio

from src.services.analytics_service import AnalyticsService
from src.services.caching_service import CachingService

logger = logging.getLogger(__name__)

class CacheWarmingService:
    def __init__(self, analytics_service: AnalyticsService, caching_service: CachingService):
        self.analytics_service = analytics_service
        self.caching_service = caching_service
        self.warming_interval = timedelta(minutes=4)  # Warm up cache every 4 minutes (before 5-minute TTL)

    def _get_first_day_of_month(self, dt: datetime) -> datetime:
        """Get the first day of the month for a given datetime"""
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _get_last_day_of_month(self, dt: datetime) -> datetime:
        """Get the last day of the month for a given datetime"""
        last_day = monthrange(dt.year, dt.month)[1]
        return dt.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

    def _get_date_ranges(self) -> List[Dict[str, datetime]]:
        """Get the predefined date ranges for the dashboard buttons"""
        now = datetime.now(timezone.utc)
        
        # Day before (48-24 hours ago)
        yesterday_end = now - timedelta(hours=24)
        yesterday_start = now - timedelta(hours=48)

        # Current month (1st of month to now)
        current_month_start = self._get_first_day_of_month(now)

        # Previous month
        prev_month = (now - timedelta(days=now.day)).replace(day=1)  # Go to 1st of previous month
        prev_month_start = self._get_first_day_of_month(prev_month)
        prev_month_end = self._get_last_day_of_month(prev_month)

        # Calculate multi-month ranges
        three_months_ago = now - timedelta(days=90)
        six_months_ago = now - timedelta(days=180)
        twelve_months_ago = now - timedelta(days=365)

        ranges = [
            {
                "name": "day_before",
                "start": yesterday_start,
                "end": yesterday_end
            },
            {
                "name": "current_month",
                "start": current_month_start,
                "end": now
            },
            {
                "name": "previous_month",
                "start": prev_month_start,
                "end": prev_month_end
            },
            {
                "name": "last_3_months",
                "start": three_months_ago,
                "end": now
            },
            {
                "name": "last_6_months",
                "start": six_months_ago,
                "end": now
            },
            {
                "name": "last_12_months",
                "start": twelve_months_ago,
                "end": now
            }
        ]
        
        # Log the ranges for debugging
        for date_range in ranges:
            logger.debug(f"Date range {date_range['name']}: {date_range['start']} to {date_range['end']}")
        
        return ranges

    async def warm_dashboard_cache(self) -> None:
        """Warm up cache for all dashboard date ranges"""
        date_ranges = self._get_date_ranges()
        
        for date_range in date_ranges:
            start_date = date_range["start"]
            end_date = date_range["end"]
            range_name = date_range["name"]
            
            # Cache dashboard metrics
            cache_key = f"dashboard_metrics:{start_date.isoformat()}:{end_date.isoformat()}"
            try:
                metrics = await self.analytics_service.get_dashboard_metrics(start_date, end_date)
                await self.caching_service.set(cache_key, metrics)
                logger.info(f"Warmed up cache for dashboard metrics: {range_name}")
            except Exception as e:
                logger.error(f"Failed to warm up cache for dashboard metrics ({range_name}): {str(e)}")

            # Cache user list for drill-down
            cache_key = f"user_list:{start_date.isoformat()}:{end_date.isoformat()}"
            try:
                users = await self.analytics_service.descope_service.search_users_by_date(
                    int(start_date.timestamp()),
                    int(end_date.timestamp())
                )
                await self.caching_service.set(cache_key, users)
                logger.info(f"Warmed up cache for user list: {range_name}")
            except Exception as e:
                logger.error(f"Failed to warm up cache for user list ({range_name}): {str(e)}")

    async def start_warming_loop(self) -> None:
        """Start the continuous cache warming loop"""
        logger.info("Starting cache warming loop")
        while True:
            try:
                await self.warm_dashboard_cache()
                await asyncio.sleep(self.warming_interval.total_seconds())
            except Exception as e:
                logger.error(f"Error in cache warming loop: {str(e)}")
                await asyncio.sleep(30)  # Wait 30 seconds before retrying on error
