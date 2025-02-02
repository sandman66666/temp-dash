import os
import asyncio
import ssl
import certifi
import aiohttp
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine, Column, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQLAlchemy setup (using SQLite for demo; replace with your DB if needed)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///daily_metrics.db")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True)
    descope_total = Column(Integer, nullable=False)
    opensearch_total = Column(Integer, nullable=True)  # Optional if you want to store more metrics
    note = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# Functions to fetch metrics

async def fetch_descope_total():
    """
    Fetch the cumulative user count from Descope.
    This uses the Descope endpoint without date filtering (since that’s how it behaves).
    """
    descope_url = os.getenv("DESCOPE_API_URL", "https://api.descope.com/v1/mgmt/user/search")
    bearer_token = os.getenv("DESCOPE_BEARER_TOKEN", "")
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    # Since the API doesn't filter by date, we just get the overall count.
    payload = {
        "tenantIds": [],
        "text": "",
        "roleNames": [],
        "loginIds": [],
        "ssoAppIds": [],
        "customAttributes": {}
    }
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.post(descope_url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                users = data.get("users", [])
                total = len(users)
                logger.debug("Fetched Descope total: %s", total)
                return total
            else:
                error_text = await response.text()
                logger.error("Descope API error: %s - %s", response.status, error_text)
                return 0

async def fetch_opensearch_total():
    """
    Fetch a cumulative count from OpenSearch.
    This could be an aggregation query over your index.
    Adjust the query as needed.
    """
    from opensearchpy import AsyncOpenSearch
    opensearch_url = os.getenv("OPENSEARCH_URL", "https://localhost:9200")
    opensearch_username = os.getenv("OPENSEARCH_USERNAME", "elkadmin")
    opensearch_password = os.getenv("OPENSEARCH_PASSWORD", "")
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    client = AsyncOpenSearch(
        hosts=[opensearch_url],
        http_auth=(opensearch_username, opensearch_password),
        verify_certs=False
    )
    # Query that counts all documents in the index.
    query = {"query": {"match_all": {}}}
    try:
        response = await client.search(index="events-v2", body=query, size=0)
        total = response.get("hits", {}).get("total", {}).get("value", 0)
        logger.debug("Fetched OpenSearch total: %s", total)
        await client.close()
        return total
    except Exception as e:
        logger.error("Error fetching OpenSearch total: %s", str(e), exc_info=True)
        await client.close()
        return 0

async def store_daily_snapshot():
    """
    Fetch metrics from Descope and OpenSearch and store them in the database.
    This function should be scheduled to run at midnight every day.
    """
    snapshot_date = datetime.now()
    logger.info("Storing daily snapshot for date: %s", snapshot_date.isoformat())
    
    descope_total = await fetch_descope_total()
    opensearch_total = await fetch_opensearch_total()
    
    # Save to the database
    db = SessionLocal()
    try:
        # Check if a snapshot for today already exists
        existing = db.query(DailyMetric).filter(DailyMetric.date == snapshot_date.date()).first()
        if existing:
            logger.info("Snapshot for today already exists, updating it.")
            existing.descope_total = descope_total
            existing.opensearch_total = opensearch_total
        else:
            new_snapshot = DailyMetric(
                date=snapshot_date.date(),
                descope_total=descope_total,
                opensearch_total=opensearch_total,
                note="Daily snapshot at midnight"
            )
            db.add(new_snapshot)
            logger.info("New snapshot created.")
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error storing snapshot: %s", str(e), exc_info=True)
    finally:
        db.close()

async def main():
    scheduler = AsyncIOScheduler()
    # Schedule the store_daily_snapshot() to run at midnight every day.
    scheduler.add_job(store_daily_snapshot, 'cron', hour=0, minute=0)
    scheduler.start()
    
    logger.info("Scheduler started. Daily snapshot job scheduled at midnight.")
    # Keep the script running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())