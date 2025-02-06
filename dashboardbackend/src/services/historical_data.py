"""
Historical data for V1 metrics
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
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
    def _spread_monthly_data(cls) -> List[Dict[str, Any]]:
        """Spread monthly data evenly across days"""
        daily_data = []
        for i in range(len(cls.V1_DATA) - 1):
            start_date = cls.V1_DATA[i]["date"]
            end_date = cls.V1_DATA[i + 1]["date"]
            days = (end_date - start_date).days

            for j in range(days):
                current_date = start_date + timedelta(days=j)
                progress = j / days
                daily_data.append({
                    "date": current_date,
                    "total_users": int(cls.V1_DATA[i]["total_users"] + progress * (cls.V1_DATA[i + 1]["total_users"] - cls.V1_DATA[i]["total_users"])),
                    "active_users": int(cls.V1_DATA[i]["active_users"] + progress * (cls.V1_DATA[i + 1]["active_users"] - cls.V1_DATA[i]["active_users"])),
                    "producers": int(cls.V1_DATA[i]["producers"] + progress * (cls.V1_DATA[i + 1]["producers"] - cls.V1_DATA[i]["producers"]))
                })

        # Add the last day
        daily_data.append(cls.V1_DATA[-1])
        return daily_data

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

        start_date = cls._ensure_timezone(start_date)
        end_date = cls._ensure_timezone(end_date)

        # Spread monthly data to daily data
        daily_data = cls._spread_monthly_data()

        # Find the closest data points before start_date and at/after end_date
        start_index = next((i for i, d in enumerate(daily_data) if d["date"] >= start_date), 0)
        end_index = next((i for i, d in enumerate(daily_data) if d["date"] > end_date), len(daily_data)) - 1

        if start_index > 0:
            start_index -= 1  # Include the day before start_date

        # Calculate the differences
        total_users = daily_data[end_index]["total_users"] - daily_data[start_index]["total_users"]
        active_users = daily_data[end_index]["active_users"] - daily_data[start_index]["active_users"]
        producers = daily_data[end_index]["producers"] - daily_data[start_index]["producers"]

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