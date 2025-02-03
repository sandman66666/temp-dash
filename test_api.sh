#!/bin/bash

echo "Testing API endpoints..."
echo "--------------------------------"

# Get current date in ISO format
END_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Get date 7 days ago
START_DATE=$(date -u -v-7d +"%Y-%m-%dT%H:%M:%SZ")

# Test 1: Get power users with date range
echo "Test 1: Get power users"
echo "Date range: $START_DATE to $END_DATE"
curl -v "http://localhost:5001/getGaugeUserCandidates?metricId=power_users&startDate=$START_DATE&endDate=$END_DATE" 2>&1 | tee /dev/tty | grep -v "^*" | python3 -m json.tool || echo "Failed to parse JSON"

echo
echo "Test 2: Get user events by ID"
curl -v "http://localhost:5001/getUserEventsById?userId=679f102daf412bba81b01e6c" 2>&1 | tee /dev/tty | grep -v "^*" | python3 -m json.tool || echo "Failed to parse JSON"

echo
echo "Test 3: Get available fields"
curl -v "http://localhost:5001/getFields" 2>&1 | tee /dev/tty | grep -v "^*" | python3 -m json.tool || echo "Failed to parse JSON"

echo
echo "Test 4: Get metrics"
curl -v "http://localhost:5001/metrics?startDate=$START_DATE&endDate=$END_DATE" 2>&1 | tee /dev/tty | grep -v "^*" | python3 -m json.tool || echo "Failed to parse JSON"

echo "Tests completed."