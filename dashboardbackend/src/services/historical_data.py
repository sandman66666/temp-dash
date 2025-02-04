"""
Historical data for V1 metrics
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from calendar import monthrange

class HistoricalData:
    # Historical data by month (cumulative totals)
    V1_DATA = [
        {
            "date": datetime(2024, 10, 1, tzinfo=timezone.utc),
            "total_users": 9770,
            "active_users": 1213,
            "producers": 1220
        },
        {
            "date": datetime(2024, 11, 1, tzinfo=timezone.utc),
            "total_users": 18634,
            "active_users": 4231,
            "producers": 4320
        },
        {
            "date": datetime(2024, 12, 1, tzinfo=timezone.utc),
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

    @classmethod
    def _ensure_timezone(cls, date: datetime) -> datetime:
        """Ensure date is timezone-aware"""
        if date.tzinfo is None:
            return date.replace(tzinfo=timezone.utc)
        return date

    @classmethod
    def _get_days_in_month(cls, date: datetime) -> int:
        """Get number of days in a month"""
        return monthrange(date.year, date.month)[1]

    @classmethod
    def _calculate_daily_growth(cls, start_value: int, end_value: int, days: int) -> float:
        """Calculate average daily growth between two values"""
        return (end_value - start_value) / days if days > 0 else 0

    @classmethod
    def _get_value_at_date(cls, target_date: datetime) -> Dict[str, int]:
        """Get values at a specific date with daily averages"""
        target_date = cls._ensure_timezone(target_date)
        
        # Before first data point
        if target_date < cls.V1_DATA[0]["date"]:
            return {
                "total_users": 0,
                "active_users": 0,
                "producers": 0
            }
            
        # After last data point
        if target_date >= cls.V1_DATA[-1]["date"]:
            return {
                "total_users": cls.V1_DATA[-1]["total_users"],
                "active_users": cls.V1_DATA[-1]["active_users"],
                "producers": cls.V1_DATA[-1]["producers"]
            }

        # Find the appropriate data points
        for i in range(len(cls.V1_DATA) - 1):
            if cls.V1_DATA[i]["date"] <= target_date < cls.V1_DATA[i + 1]["date"]:
                # Calculate days between points
                days_between = (cls.V1_DATA[i + 1]["date"] - cls.V1_DATA[i]["date"]).days
                days_from_start = (target_date - cls.V1_DATA[i]["date"]).days

                # Calculate daily growth rates
                total_users_daily = cls._calculate_daily_growth(
                    cls.V1_DATA[i]["total_users"],
                    cls.V1_DATA[i + 1]["total_users"],
                    days_between
                )
                active_users_daily = cls._calculate_daily_growth(
                    cls.V1_DATA[i]["active_users"],
                    cls.V1_DATA[i + 1]["active_users"],
                    days_between
                )
                producers_daily = cls._calculate_daily_growth(
                    cls.V1_DATA[i]["producers"],
                    cls.V1_DATA[i + 1]["producers"],
                    days_between
                )

                # Calculate values at target date
                total_users = int(cls.V1_DATA[i]["total_users"] + (total_users_daily * days_from_start))
                active_users = int(cls.V1_DATA[i]["active_users"] + (active_users_daily * days_from_start))
                producers = int(cls.V1_DATA[i]["producers"] + (producers_daily * days_from_start))
                
                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "producers": producers,
                    "daily_growth": {
                        "total_users": total_users_daily,
                        "active_users": active_users_daily,
                        "producers": producers_daily
                    }
                }
        
        return {
            "total_users": cls.V1_DATA[-1]["total_users"],
            "active_users": cls.V1_DATA[-1]["active_users"],
            "producers": cls.V1_DATA[-1]["producers"],
            "daily_growth": {
                "total_users": 0,
                "active_users": 0,
                "producers": 0
            }
        }

    @classmethod
    def get_v1_metrics(cls, start_date: datetime, end_date: datetime, include_v1: bool = True) -> Dict[str, Any]:
        """Get V1 metrics for the specific time range with daily averages"""
        if not include_v1:
            return {
                "total_users": 0,
                "active_users": 0,
                "producers": 0,
                "daily_averages": {
                    "total_users": 0,
                    "active_users": 0,
                    "producers": 0
                }
            }

        # Get values and daily growth rates at start and end dates
        end_data = cls._get_value_at_date(end_date)
        start_data = cls._get_value_at_date(start_date - timedelta(days=1))

        # Calculate activity during time range
        total_users = end_data["total_users"] - start_data["total_users"]
        active_users = end_data["active_users"] - start_data["active_users"]
        producers = end_data["producers"] - start_data["producers"]

        # Calculate days in range
        days_in_range = (end_date - start_date).days + 1

        # Calculate daily averages
        daily_averages = {
            "total_users": total_users / days_in_range if days_in_range > 0 else 0,
            "active_users": active_users / days_in_range if days_in_range > 0 else 0,
            "producers": producers / days_in_range if days_in_range > 0 else 0
        }

        return {
            "total_users": total_users,
            "active_users": active_users,
            "producers": producers,
            "daily_averages": daily_averages
        }