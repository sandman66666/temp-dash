import json
from datetime import datetime, timedelta
import os

def interpolate(start_val, end_val, num_points):
    """Linear interpolation between two values"""
    if num_points <= 1:
        return []
    step = (end_val - start_val) / (num_points - 1)
    return [int(start_val + step * i) for i in range(num_points)]

def generate_daily_metrics():
    # Known data points
    known_points = {
        "2024-10-01": {"total_users": 0, "active_users": 0, "producers": 0},
        "2024-10-31": {"total_users": 9770, "active_users": 1213, "producers": 551},
        "2024-11-30": {"total_users": 18634, "active_users": 4231, "producers": 1923},
        "2024-12-31": {"total_users": 48850, "active_users": 9863, "producers": 4483},
        "2025-01-26": {"total_users": 55000, "active_users": 16560, "producers": 7527}
    }

    # Convert dates to datetime objects
    date_points = sorted([(datetime.strptime(d, "%Y-%m-%d"), metrics) 
                         for d, metrics in known_points.items()])

    daily_metrics = {}
    
    # Interpolate between each pair of known points
    for i in range(len(date_points) - 1):
        start_date, start_metrics = date_points[i]
        end_date, end_metrics = date_points[i + 1]
        
        # Calculate number of days between points
        num_days = (end_date - start_date).days + 1
        
        # Generate dates
        dates = [start_date + timedelta(days=x) for x in range(num_days)]
        
        # Interpolate each metric
        for metric in ['total_users', 'active_users', 'producers']:
            values = interpolate(start_metrics[metric], end_metrics[metric], num_days)
            
            # Add to daily metrics
            for date, value in zip(dates, values):
                date_str = date.strftime("%Y-%m-%d")
                if date_str not in daily_metrics:
                    daily_metrics[date_str] = {}
                daily_metrics[date_str][metric] = value

    # Add the final day
    final_date, final_metrics = date_points[-1]
    daily_metrics[final_date.strftime("%Y-%m-%d")] = final_metrics

    # Create the full JSON structure
    json_data = {
        "metadata": {
            "start_date": "2024-10-01",
            "end_date": "2025-01-26",
            "last_updated": "2025-01-26"
        },
        "daily_metrics": daily_metrics
    }

    # Write to file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "src", "data", "historical_metrics.json")
    
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=4)

if __name__ == "__main__":
    generate_daily_metrics()
