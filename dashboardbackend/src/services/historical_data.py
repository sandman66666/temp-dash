"""
Historical data for V1 metrics
"""
from datetime import datetime, timezone
from typing import Dict, Any

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
    def _get_value_at_date(cls, target_date: datetime) -> Dict[str, int]:
        """Get cumulative values at a specific date"""
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

        # Find the appropriate data point
        for i in range(len(cls.V1_DATA) - 1):
            if cls.V1_DATA[i]["date"] <= target_date < cls.V1_DATA[i + 1]["date"]:
                # Linear interpolation between points
                days_between = (cls.V1_DATA[i + 1]["date"] - cls.V1_DATA[i]["date"]).days
                days_from_start = (target_date - cls.V1_DATA[i]["date"]).days
                ratio = days_from_start / days_between

                total_users = int(cls.V1_DATA[i]["total_users"] + 
                                (cls.V1_DATA[i + 1]["total_users"] - cls.V1_DATA[i]["total_users"]) * ratio)
                active_users = int(cls.V1_DATA[i]["active_users"] + 
                                 (cls.V1_DATA[i + 1]["active_users"] - cls.V1_DATA[i]["active_users"]) * ratio)
                producers = int(cls.V1_DATA[i]["producers"] + 
                              (cls.V1_DATA[i + 1]["producers"] - cls.V1_DATA[i]["producers"]) * ratio)
                
                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "producers": producers
                }
        
        return {
            "total_users": cls.V1_DATA[-1]["total_users"],
            "active_users": cls.V1_DATA[-1]["active_users"],
            "producers": cls.V1_DATA[-1]["producers"]
        }

    @classmethod
    def get_v1_metrics(cls, start_date: datetime, end_date: datetime, include_v1: bool = True) -> Dict[str, int]:
        """Get V1 metrics at the end date (to be added to existing metrics)"""
        if not include_v1:
            return {
                "total_users": 0,
                "active_users": 0,
                "producers": 0
            }

        # Return cumulative values at end date
        return cls._get_value_at_date(end_date)