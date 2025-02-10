import asyncio
import time
import logging
from datetime import datetime, timezone, timedelta
from src.services.descope_service import DescopeService

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    service = DescopeService()
    logger.info(f"Using project ID: {service.project_id}")
    logger.info(f"Using bearer token: {service.bearer_token[:10]}...")
    
    # Get timestamps for the date range
    seven_days_ago = datetime(2025, 2, 3, tzinfo=timezone.utc)  # 7 days ago
    three_days_ago = datetime(2025, 2, 7, tzinfo=timezone.utc)  # 3 days ago
    
    seven_days_ago_ts = int(seven_days_ago.timestamp())
    three_days_ago_ts = int(three_days_ago.timestamp())
    
    print(f"Searching users from {seven_days_ago.isoformat()} to {three_days_ago.isoformat()}")
    users = await service.search_users_by_date(seven_days_ago_ts, three_days_ago_ts)
    
    print(f"\nFound {len(users)} users in the date range:")
    for user in users:
        created_time = int(user.get('createdTime', 0))
        print(f"Email: {user.get('email')}, Created: {datetime.fromtimestamp(created_time, timezone.utc).isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
