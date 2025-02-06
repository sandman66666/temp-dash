from datetime import datetime
from typing import Dict, Any
from .base_metrics import BaseMetrics

class UserMetrics(BaseMetrics):
    def __init__(self, start_date: datetime, end_date: datetime):
        super().__init__(start_date, end_date)
        self.total_users = self.get_empty_metric()
        self.producers = self.get_empty_metric()

    async def fetch_metrics(self, analytics_service):
        """Fetch all user metrics"""
        self.total_users = await self._get_total_users(analytics_service)
        self.producers = await self._get_producers(analytics_service)

    async def _get_total_users(self, analytics_service) -> Dict[str, Any]:
        """Get total number of users in time range"""
        return await analytics_service._get_total_users(self.start_date, self.end_date)

    async def _get_producers(self, analytics_service) -> Dict[str, Any]:
        """Get count of producers in time range"""
        return await analytics_service._get_producers(self.start_date, self.end_date)

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all user metrics"""
        return {
            "total_users": self.total_users,
            "producers": self.producers
        }

    def combine_with_historical_data(self, historical_data: Dict[str, Any]):
        """Combine metrics with historical data"""
        self.total_users["value"] += historical_data["total_users"]
        self.total_users["daily_average"] += historical_data["daily_averages"]["total_users"]
        
        self.producers["value"] += historical_data["producers"]
        self.producers["daily_average"] += historical_data["daily_averages"]["producers"]