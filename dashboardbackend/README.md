# Analytics Dashboard Backend

This is the backend service for the Analytics Dashboard, providing APIs for fetching and analyzing user activity and metrics.

## Project Structure

The project is organized as follows:

```
dashboardbackend/
├── src/
│   ├── services/
│   │   ├── analytics_service.py
│   │   ├── metrics_service.py
│   │   ├── historical_data_service.py
│   │   ├── descope_service.py
│   │   ├── caching_service.py
│   │   └── opensearch_service.py
│   ├── utils/
│   │   └── query_builder.py
│   ├── api/
│   │   └── metrics.py
│   └── core/
│       └── __init__.py
├── tests/
│   └── test_analytics_service.py
├── requirements.txt
├── run.py
└── README.md
```

## Services

- `analytics_service.py`: Main service that orchestrates data fetching and processing.
- `metrics_service.py`: Handles all metrics-related operations (user, content, producer metrics). This service now includes the AnalyticsMetricsService, which consolidates functionality previously spread across multiple files.
- `historical_data_service.py`: Provides historical data for V1 metrics.
- `descope_service.py`: Handles interactions with the Descope API for user management and authentication.
- `caching_service.py`: Manages caching of data to improve performance. This service now accepts a Redis client for better flexibility and testability.
- `opensearch_service.py`: Handles interactions with OpenSearch for data querying and aggregation.

## Recent Changes

- Consolidated metrics-related functionality into the AnalyticsMetricsService within metrics_service.py.
- Updated the CachingService to accept a Redis client, improving its flexibility and testability.
- Streamlined the project structure by removing redundant files and consolidating related functionality.

## Setup and Running

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up environment variables (see `.env.example` for required variables).

3. Run the server:
   ```
   python run.py
   ```

The server will start running on `http://0.0.0.0:5001` by default.

## Testing

To run the tests:

```
pytest
```

## API Endpoints

- `/metrics`: Get dashboard metrics
- `/metrics/user-stats`: Get user statistics
- `/metrics/user-events`: Get user events

For detailed API documentation, please refer to the API specification document.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.