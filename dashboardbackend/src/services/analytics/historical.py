"""
Historical data service for V1 metrics
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple

class HistoricalDataService:
    """Handles V1 historical data from Oct 1, 2024 to Jan 26, 2025"""

    # Historical data points with cumulative totals
    V1_DATA = [
        {
            "date": datetime(2024, 10, 1, tzinfo=timezone.utc),
            "total_users": 0,  # Starting point
            "active_users": 0,
            "producers": 0
        },
        {
            "date": datetime(2024, 10, 31, tzinfo=timezone.utc),
            "total_users": 9770,
            "active_users": 1213,
            "producers": 1220
        },
        {
            "date": datetime(2024, 11, 30, tzinfo=timezone.utc),
            "total_users": 18634,
            "active_users": 4231,
            "producers": 4320
        },
        {
            "date": datetime(2024, 12, 31, tzinfo=timezone.utc),
            "total_users": 27058,
            "active_users": 9863,
            "producers": 9830
        },
        {
            "date": datetime(2025, 1, 26, tzinfo=timezone.utc),
            "total_users": 48850,
            "active_users": 16560,
            "producers": 16800
        }
    ]

    def __init__(self):
        self.min_date = datetime(2024, 10, 1, tzinfo=timezone.utc)
        self.max_date = datetime(2025, 1, 26, tzinfo=timezone.utc)
        self.latest_v1_data = self.V1_DATA[-1]

    def _ensure_timezone(self, date: datetime) -> datetime:
        """Ensure date is timezone-aware"""
        if date.tzinfo is None:
            return date.replace(tzinfo=timezone.utc)
        return date

    def _get_metrics_for_range(self, start_date: datetime, end_date: datetime) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Get metrics at start and end of range"""
        start_date = self._ensure_timezone(start_date)
        end_date = self._ensure_timezone(end_date)

        # Find metrics at start date
        start_metrics = None
        for i, data in enumerate(self.V1_DATA):
            if data["date"] <= start_date:
                start_metrics = data
            else:
                break

        # Find metrics at end date
        end_metrics = None
        for data in reversed(self.V1_DATA):
            if data["date"] <= end_date:
                end_metrics = data
                break

        # Use initial values if no data found
        if not start_metrics:
            start_metrics = self.V1_DATA[0]
        if not end_metrics:
            end_metrics = self.V1_DATA[0]

        return start_metrics, end_metrics

    def get_v1_metrics(self, start_date: datetime, end_date: datetime, include_v1: bool = True) -> Dict[str, Any]:
        """Get V1 metrics for the specific time range"""
        # Return empty metrics if V1 data is not needed
        if not include_v1:
            return self._get_empty_metrics()

        # Return empty metrics if the date range is entirely after V1 end date
        if start_date > self.max_date:
            return self._get_empty_metrics()

        # Ensure dates are timezone-aware
        start_date = self._ensure_timezone(start_date)
        end_date = self._ensure_timezone(end_date)

        # Don't look at data before Oct 1st 2024
        if start_date < self.min_date:
            start_date = self.min_date

        # Cap end date at V1 end date
        if end_date > self.max_date:
            end_date = self.max_date

        # Get metrics at start and end of range
        start_metrics, end_metrics = self._get_metrics_for_range(start_date - timedelta(days=1), end_date)

        # Calculate deltas
        metrics = {
            "total_users": end_metrics["total_users"] - start_metrics["total_users"],
            "active_users": end_metrics["active_users"] - start_metrics["active_users"],
            "producers": end_metrics["producers"] - start_metrics["producers"]
        }

        # Calculate daily averages
        days_in_range = (end_date - start_date).days + 1
        if days_in_range < 1:
            days_in_range = 1

        daily_averages = {
            "total_users": metrics["total_users"] / days_in_range,
            "active_users": metrics["active_users"] / days_in_range,
            "producers": metrics["producers"] / days_in_range
        }

        return {
            "total_users": metrics["total_users"],
            "active_users": metrics["active_users"],
            "producers": metrics["producers"],
            "daily_averages": daily_averages,
            "cumulative": {
                "total_users": end_metrics["total_users"],
                "active_users": end_metrics["active_users"],
                "producers": end_metrics["producers"]
            }
        }

    def get_all_time_metrics(self) -> Dict[str, Any]:
        """Get all-time metrics (always includes full V1 data)"""
        # Always use the last V1 data point for all-time metrics
        # This represents the cumulative totals up to Jan 26, 2025
        metrics = {
            "total_users": self.latest_v1_data["total_users"],
            "active_users": self.latest_v1_data["active_users"],
            "producers": self.latest_v1_data["producers"]
        }

        # Calculate total days from Oct 1, 2024 to Jan 26, 2025
        total_days = (self.max_date - self.min_date).days + 1
        if total_days < 1:
            total_days = 1

        daily_averages = {
            "total_users": metrics["total_users"] / total_days,
            "active_users": metrics["active_users"] / total_days,
            "producers": metrics["producers"] / total_days
        }

        return {
            "total_users": metrics["total_users"],
            "active_users": metrics["active_users"],
            "producers": metrics["producers"],
            "daily_averages": daily_averages,
            "start_date": self.min_date.isoformat(),
            "end_date": self.max_date.isoformat()
        }

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            "total_users": 0,
            "active_users": 0,
            "producers": 0,
            "daily_averages": {
                "total_users": 0,
                "active_users": 0,
                "producers": 0
            },
            "cumulative": {
                "total_users": 0,
                "active_users": 0,
                "producers": 0
            }
        }