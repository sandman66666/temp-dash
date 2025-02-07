"""
Historical data service for fetching and processing historical metrics
"""
from typing import Dict, Any, Optional
import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class HistoricalDataService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_historical_data()

    def _load_historical_data(self):
        """Load historical data from JSON file"""
        try:
            data_file = os.path.join(os.path.dirname(__file__), '../data/historical_metrics.json')
            with open(data_file, 'r') as f:
                self.historical_data = json.load(f)
            
            # Convert date strings to datetime objects
            self.min_date = datetime.strptime(self.historical_data['metadata']['start_date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            self.max_date = datetime.strptime(self.historical_data['metadata']['end_date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
            self.logger.info(f"Loaded historical data from {self.min_date} to {self.max_date}")
        except Exception as e:
            self.logger.error(f"Failed to load historical data: {e}")
            self.historical_data = None
            self.min_date = None
            self.max_date = None

    def _ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware"""
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    def _find_nearest_date(self, target_date: datetime, direction: str = 'before') -> Optional[str]:
        """Find nearest date in historical data
        
        Args:
            target_date: Target date to find nearest for
            direction: Either 'before' or 'after'
        
        Returns:
            Date string in YYYY-MM-DD format or None if not found
        """
        target_str = target_date.strftime('%Y-%m-%d')
        dates = sorted(self.historical_data['daily_metrics'].keys())
        
        # If exact date exists, return it
        if target_str in dates:
            return target_str
            
        # Find nearest date
        for i, date in enumerate(dates):
            if direction == 'before':
                if date > target_str:
                    return dates[i-1] if i > 0 else None
            else:
                if date >= target_str:
                    return date
                    
        # If we get here and want date before, return last date
        if direction == 'before':
            return dates[-1]
        return None

    def get_v1_metrics(self, start_date: datetime, end_date: datetime, include_v1: bool = True) -> Dict[str, Any]:
        """Get historical metrics for date range"""
        if not include_v1 or not self.historical_data:
            return {}

        # Ensure dates are timezone-aware
        start_date = self._ensure_timezone(start_date)
        end_date = self._ensure_timezone(end_date)

        # Find nearest dates in our data
        start_date_str = self._find_nearest_date(start_date, 'before')
        end_date_str = self._find_nearest_date(end_date, 'before')

        if not start_date_str or not end_date_str:
            self.logger.warning(f"No historical data found for date range: {start_date} to {end_date}")
            return {}

        # Get metrics for start and end dates
        start_metrics = self.historical_data['daily_metrics'][start_date_str]
        end_metrics = self.historical_data['daily_metrics'][end_date_str]

        self.logger.debug(f"Using metrics from {start_date_str} to {end_date_str}")
        self.logger.debug(f"Start metrics: {start_metrics}")
        self.logger.debug(f"End metrics: {end_metrics}")

        # Calculate growth
        total_days = (end_date - start_date).days + 1
        growth = {
            'total_users': end_metrics['total_users'] - start_metrics['total_users'],
            'active_users': end_metrics['active_users'] - start_metrics['active_users'],
            'producers': end_metrics['producers'] - start_metrics['producers']
        }

        # Calculate daily averages
        daily_averages = {
            metric: value / total_days if total_days > 0 else 0
            for metric, value in growth.items()
        }

        return {
            'daily_averages': daily_averages,
            'cumulative': growth,
            'previous': start_metrics
        }