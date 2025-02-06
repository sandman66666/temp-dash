from datetime import datetime, timezone
from typing import Dict, Any

def ensure_timezone(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def calculate_delta(current: float, previous: float) -> float:
    """Calculate percentage change"""
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous) * 100

def create_metric_object(value: float, previous_value: float, daily_average: float) -> Dict[str, Any]:
    """Create a metric object with calculated trend and change percentage"""
    delta = calculate_delta(value, previous_value)
    trend = "up" if delta > 0 else "down" if delta < 0 else "neutral"
    return {
        "value": value,
        "previousValue": previous_value,
        "trend": trend,
        "changePercentage": round(delta, 2),
        "daily_average": daily_average
    }

def get_empty_metric() -> Dict[str, Any]:
    """Return an empty metric object"""
    return create_metric_object(0, 0, 0)

def format_date_iso(dt: datetime) -> str:
    """Format datetime to ISO string"""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

class BaseMetrics:
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = ensure_timezone(start_date)
        self.end_date = ensure_timezone(end_date)
        self.days_in_range = (self.end_date - self.start_date).days + 1

    def get_date_range(self) -> Dict[str, str]:
        """Get the date range for the metrics"""
        return {
            "start": format_date_iso(self.start_date),
            "end": format_date_iso(self.end_date)
        }

    def calculate_daily_average(self, total: float) -> float:
        """Calculate the daily average for a given total"""
        return total / self.days_in_range if self.days_in_range > 0 else 0

    def create_metric(self, value: float, previous_value: float) -> Dict[str, Any]:
        """Create a metric object with calculated daily average"""
        daily_average = self.calculate_daily_average(value)
        return create_metric_object(value, previous_value, daily_average)