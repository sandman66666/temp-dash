from datetime import datetime
from typing import Dict, Any
from .base_metrics import BaseMetrics

class ActivityMetrics(BaseMetrics):
    def __init__(self, start_date: datetime, end_date: datetime):
        super().__init__(start_date, end_date)
        self.thread_users = self.get_empty_metric()
        self.sketch_users = self.get_empty_metric()
        self.render_users = self.get_empty_metric()
        self.medium_chat_users = self.get_empty_metric()
        self.power_users = self.get_empty_metric()

    async def fetch_metrics(self, analytics_service):
        """Fetch all activity metrics"""
        self.thread_users = await self._get_thread_users(analytics_service)
        self.sketch_users = await self._get_sketch_users(analytics_service)
        self.render_users = await self._get_render_users(analytics_service)
        self.medium_chat_users = await self._get_medium_chat_users(analytics_service)
        self.power_users = await self._get_power_users(analytics_service)

    async def _get_thread_users(self, analytics_service) -> Dict[str, Any]:
        """Get count of users with message threads in time range"""
        return await analytics_service._get_thread_users(self.start_date, self.end_date)

    async def _get_sketch_users(self, analytics_service) -> Dict[str, Any]:
        """Get count of users who have uploaded sketches in time range"""
        return await analytics_service._get_sketch_users(self.start_date, self.end_date)

    async def _get_render_users(self, analytics_service) -> Dict[str, Any]:
        """Get count of users who have completed renders in time range"""
        return await analytics_service._get_render_users(self.start_date, self.end_date)

    async def _get_medium_chat_users(self, analytics_service) -> Dict[str, Any]:
        """Get users with 5-20 message threads in time range"""
        return await analytics_service._get_medium_chat_users(self.start_date, self.end_date)

    async def _get_power_users(self, analytics_service) -> Dict[str, Any]:
        """Get users with more than 20 message threads in time range"""
        return await analytics_service._get_power_users(self.start_date, self.end_date)

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all activity metrics"""
        return {
            "thread_users": self.thread_users,
            "sketch_users": self.sketch_users,
            "render_users": self.render_users,
            "medium_chat_users": self.medium_chat_users,
            "power_users": self.power_users
        }