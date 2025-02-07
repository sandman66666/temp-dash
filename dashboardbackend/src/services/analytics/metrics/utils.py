"""
Utility functions for metrics calculations
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)

def ensure_timezone(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def calculate_delta(curr_value: int, prev_value: int, daily_average: float = 0) -> Dict[str, Any]:
    """Calculate delta between current and previous values"""
    delta = curr_value - prev_value
    
    return {
        "value": curr_value,
        "previousValue": prev_value,
        "trend": "up" if delta > 0 else "down" if delta < 0 else "neutral",
        "changePercentage": round((delta / prev_value * 100) if prev_value > 0 else 100 if delta > 0 else 0, 2),
        "daily_average": daily_average
    }

def create_metric_object(
    metric_id: str,
    name: str,
    description: str,
    category: str,
    current_value: Union[int, Dict[str, Any]],
    v1_value: int = 0
) -> Dict[str, Any]:
    """Create a standardized metric object"""
    logger.debug(f"Creating metric object for {metric_id}")
    logger.debug(f"Input - current_value: {current_value}, v1_value: {v1_value}")

    if isinstance(current_value, int):
        current_value = {
            "value": current_value,
            "previousValue": 0,
            "trend": "neutral",
            "changePercentage": 0,
            "daily_average": 0
        }

    total_value = current_value["value"] + v1_value
    previous_value = current_value.get("previousValue", 0)
    days_in_range = current_value.get("days_in_range", 1)
    daily_average = current_value.get("daily_average", total_value / days_in_range if days_in_range > 0 else 0)

    # Calculate trend and change percentage
    if total_value > previous_value:
        trend = "up"
        change_percentage = (total_value - previous_value) / previous_value * 100 if previous_value > 0 else 100
    elif total_value < previous_value:
        trend = "down"
        change_percentage = (previous_value - total_value) / previous_value * 100 if previous_value > 0 else 100
    else:
        trend = "stable"
        change_percentage = 0

    metric = {
        "id": metric_id,
        "name": name,
        "description": description,
        "category": category,
        "interval": "daily",
        "data": {
            "value": total_value,
            "previousValue": previous_value,
            "trend": trend,
            "changePercentage": round(change_percentage, 2),
            "daily_average": daily_average
        }
    }

    logger.debug(f"Created metric object: {metric}")
    return metric

def get_empty_metric() -> Dict[str, Any]:
    """Return empty metric structure"""
    return {
        "value": 0,
        "previousValue": 0,
        "trend": "neutral",
        "daily_average": 0,
        "changePercentage": 0
    }

def format_date_iso(dt: datetime) -> str:
    """Format datetime to ISO string"""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")