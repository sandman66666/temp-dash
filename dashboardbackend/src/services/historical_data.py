"""
Historical data for V1 metrics
"""
from datetime import datetime, timezone
from typing import Dict, Any

class HistoricalData:
    # Historical data by month
    V1_DATA = [
        {
            "date": datetime(2023, 10, 1, tzinfo=timezone.utc),
            "total_users": 9770,
            "active_users": 1213
        },
        {
            "date": datetime(2023, 11, 1, tzinfo=timezone.utc),
            "total_users": 18634,
            "active_users": 4231
        },
        {
            "date": datetime(2023, 12, 1, tzinfo=timezone.utc),
            "total_users": 27058,
            "active_users": 9863
        },
        {
            "date": datetime(2024, 1, 26, tzinfo=timezone.utc),
            "total_users": 48850,
            "active_users": 16560
        }
    ]

    @classmethod
    def _ensure_timezone(cls, date: datetime) -> datetime:
        """Ensure date is timezone-aware"""
        if date.tzinfo is None:
            return date.replace(tzinfo=timezone.utc)
        return date

    @classmethod
    def _find_surrounding_data_points(cls, target_date: datetime):
        """Find the data points before and after the target date"""
        target_date = cls._ensure_timezone(target_date)
        
        # Return zeros if before first data point
        if target_date < cls.V1_DATA[0]["date"]:
            return None, cls.V1_DATA[0]
            
        # Return last data point if after last data point
        if target_date > cls.V1_DATA[-1]["date"]:
            return cls.V1_DATA[-1], None

        # Find surrounding points
        for i in range(len(cls.V1_DATA) - 1):
            if cls.V1_DATA[i]["date"] <= target_date <= cls.V1_DATA[i + 1]["date"]:
                return cls.V1_DATA[i], cls.V1_DATA[i + 1]
        
        return cls.V1_DATA[-1], None

    @classmethod
    def _interpolate_value(cls, date: datetime, start_point: Dict[str, Any], end_point: Dict[str, Any], key: str) -> int:
        """Interpolate value between two data points"""
        if not start_point:
            return 0
        if not end_point:
            return start_point[key]

        total_days = (end_point["date"] - start_point["date"]).days
        if total_days == 0:
            return start_point[key]

        days_from_start = (date - start_point["date"]).days
        value_diff = end_point[key] - start_point[key]
        interpolated = start_point[key] + (value_diff * (days_from_start / total_days))
        return int(interpolated)

    @classmethod
    def get_v1_metrics(cls, start_date: datetime, end_date: datetime, include_v1: bool = True) -> Dict[str, int]:
        """Get V1 metrics for a specific date range"""
        if not include_v1:
            return {
                "total_users": 0,
                "active_users": 0
            }

        start_date = cls._ensure_timezone(start_date)
        end_date = cls._ensure_timezone(end_date)

        # Find surrounding data points for start and end dates
        start_before, start_after = cls._find_surrounding_data_points(start_date)
        end_before, end_after = cls._find_surrounding_data_points(end_date)

        # Get interpolated values for start and end dates
        start_total = cls._interpolate_value(start_date, start_before, start_after, "total_users")
        start_active = cls._interpolate_value(start_date, start_before, start_after, "active_users")
        end_total = cls._interpolate_value(end_date, end_before, end_after, "total_users")
        end_active = cls._interpolate_value(end_date, end_before, end_after, "active_users")

        # Return the difference in values over the date range
        return {
            "total_users": end_total - start_total,
            "active_users": end_active - start_active
        }