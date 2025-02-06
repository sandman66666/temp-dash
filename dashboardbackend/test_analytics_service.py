import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.analytics_service import AnalyticsService
from src.services.historical_data import HistoricalData

@pytest.fixture
def mock_opensearch():
    return AsyncMock()

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def analytics_service(mock_opensearch, mock_redis):
    return AnalyticsService(mock_opensearch, mock_redis)

@pytest.mark.asyncio
async def test_get_dashboard_metrics_with_historical_data(analytics_service):
    start_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

    # Mock the historical data
    with patch.object(HistoricalData, 'get_v1_metrics') as mock_get_v1_metrics:
        mock_get_v1_metrics.return_value = {
            "total_users": 1000,
            "active_users": 500,
            "producers": 100,
            "daily_averages": {
                "total_users": 50,
                "active_users": 25,
                "producers": 5
            }
        }

        # Mock OpenSearch responses
        analytics_service.opensearch.search = AsyncMock(return_value={
            "aggregations": {
                "unique_users": {"value": 200},
                "users": {"buckets": [{"key": "user1"}, {"key": "user2"}]}
            }
        })

        # Mock Descope API call
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "users": [
                    {"customAttributes": {"v2UserId": "user1"}, "email": "user1@example.com"},
                    {"customAttributes": {"v2UserId": "user2"}, "email": "user2@example.com"}
                ]
            })

            result = await analytics_service.get_dashboard_metrics(start_date, end_date)

    # Assert the combined results
    assert result["metrics"][0]["id"] == "descope_users"
    assert result["metrics"][0]["data"]["value"] == 1200  # 1000 from historical + 200 from OpenSearch
    assert result["metrics"][0]["data"]["daily_average"] == 50  # From historical data

    assert result["metrics"][1]["id"] == "thread_users"
    assert result["metrics"][1]["data"]["value"] == 700  # 500 from historical + 200 from OpenSearch
    assert result["metrics"][1]["data"]["daily_average"] == 25  # From historical data

    assert result["metrics"][6]["id"] == "producers"
    assert result["metrics"][6]["data"]["value"] == 102  # 100 from historical + 2 from OpenSearch
    assert result["metrics"][6]["data"]["daily_average"] == 5  # From historical data

@pytest.mark.asyncio
async def test_get_dashboard_metrics_spanning_historical_and_opensearch(analytics_service):
    start_date = datetime(2024, 9, 15, tzinfo=timezone.utc)  # Before historical data
    end_date = datetime(2025, 1, 15, tzinfo=timezone.utc)    # After historical data

    # Mock the historical data
    with patch.object(HistoricalData, 'get_v1_metrics') as mock_get_v1_metrics:
        mock_get_v1_metrics.return_value = {
            "total_users": 2000,
            "active_users": 1000,
            "producers": 200,
            "daily_averages": {
                "total_users": 100,
                "active_users": 50,
                "producers": 10
            }
        }

        # Mock OpenSearch responses
        analytics_service.opensearch.search = AsyncMock(return_value={
            "aggregations": {
                "unique_users": {"value": 500},
                "users": {"buckets": [{"key": f"user{i}"} for i in range(1, 6)]}
            }
        })

        # Mock Descope API call
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "users": [
                    {"customAttributes": {"v2UserId": f"user{i}"}, "email": f"user{i}@example.com"}
                    for i in range(1, 6)
                ]
            })

            result = await analytics_service.get_dashboard_metrics(start_date, end_date)

    # Assert the combined results
    assert result["metrics"][0]["id"] == "descope_users"
    assert result["metrics"][0]["data"]["value"] == 2500  # 2000 from historical + 500 from OpenSearch
    assert abs(result["metrics"][0]["data"]["daily_average"] - 100) < 1  # Approximately 100

    assert result["metrics"][1]["id"] == "thread_users"
    assert result["metrics"][1]["data"]["value"] == 1500  # 1000 from historical + 500 from OpenSearch
    assert abs(result["metrics"][1]["data"]["daily_average"] - 50) < 1  # Approximately 50

    assert result["metrics"][6]["id"] == "producers"
    assert result["metrics"][6]["data"]["value"] == 205  # 200 from historical + 5 from OpenSearch
    assert abs(result["metrics"][6]["data"]["daily_average"] - 10) < 1  # Approximately 10

@pytest.mark.asyncio
async def test_get_total_users(analytics_service):
    start_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

    # Mock Descope API call
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(side_effect=[
            {"users": [{"id": f"user{i}"} for i in range(1000)]},  # End date response
            {"users": [{"id": f"user{i}"} for i in range(800)]}    # Start date response
        ])

        result = await analytics_service._get_total_users(start_date, end_date)

    assert result["value"] == 200  # 1000 - 800
    assert result["previousValue"] == 800
    assert result["trend"] == "up"
    assert result["changePercentage"] == 25.0  # (200 / 800) * 100
    assert abs(result["daily_average"] - 3.28) < 0.01  # 200 / 61 days

@pytest.mark.asyncio
async def test_get_user_events(analytics_service):
    start_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
    trace_id = "test_user_id"

    # Mock OpenSearch response
    analytics_service.opensearch.search = AsyncMock(return_value={
        "hits": {
            "hits": [
                {"_source": {"event_name": "login", "timestamp": "2024-11-15T12:00:00Z"}},
                {"_source": {"event_name": "message_sent", "timestamp": "2024-12-01T15:30:00Z"}}
            ]
        }
    })

    result = await analytics_service.get_user_events(trace_id, start_date, end_date)

    assert len(result) == 2
    assert result[0]["event_name"] == "login"
    assert result[1]["event_name"] == "message_sent"

@pytest.mark.asyncio
async def test_get_user_statistics(analytics_service):
    start_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
    gauge_type = "thread_users"

    # Mock OpenSearch responses
    analytics_service.opensearch.search = AsyncMock(side_effect=[
        # Message counts
        {"aggregations": {"users": {"buckets": [
            {"key": "user1", "doc_count": 15},
            {"key": "user2", "doc_count": 25},
        ]}}},
        # Sketch counts
        {"aggregations": {"users": {"buckets": [
            {"key": "user1", "doc_count": 5},
            {"key": "user2", "doc_count": 10},
        ]}}},
        # Render counts
        {"aggregations": {"users": {"buckets": [
            {"key": "user1", "doc_count": 2},
            {"key": "user2", "doc_count": 4},
        ]}}}
    ])

    # Mock Descope API call
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
            "users": [
                {"customAttributes": {"v2UserId": "user1"}, "email": "user1@example.com"},
                {"customAttributes": {"v2UserId": "user2"}, "email": "user2@example.com"}
            ]
        })

        result = await analytics_service.get_user_statistics(start_date, end_date, gauge_type)

    assert len(result) == 2
    assert result[0]["email"] == "user2@example.com"
    assert result[0]["messageCount"] == 25
    assert result[0]["sketchCount"] == 10
    assert result[0]["renderCount"] == 4
    assert result[1]["email"] == "user1@example.com"
    assert result[1]["messageCount"] == 15
    assert result[1]["sketchCount"] == 5
    assert result[1]["renderCount"] == 2

if __name__ == "__main__":
    pytest.main()