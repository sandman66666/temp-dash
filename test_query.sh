#!/bin/bash

# Check if environment variables are set
if [ -z "$OPENSEARCH_USERNAME" ] || [ -z "$OPENSEARCH_PASSWORD" ]; then
    echo "Please set OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD environment variables"
    echo "Example:"
    echo "export OPENSEARCH_USERNAME=elkadmin"
    echo "export OPENSEARCH_PASSWORD=your_password"
    exit 1
fi

# Use environment variables for authentication
USERNAME="$OPENSEARCH_USERNAME"
PASSWORD="$OPENSEARCH_PASSWORD"

echo "Running OpenSearch query tests..."
echo "--------------------------------"

# Test 1: Simple query to find any events for a trace_id without .keyword
echo "Test 1: Simple query without .keyword"
curl -X POST "https://localhost:9200/events-v2/_search" \
-u "${USERNAME}:${PASSWORD}" \
-k \
-H "Content-Type: application/json" \
-d '{
  "size": 1,
  "query": {
    "term": {
      "trace_id": "67a0ee088714f09f89d36047"
    }
  }
}'

echo -e "\n\n"

# Test 2: Simple query to find any events for a trace_id with .keyword
echo "Test 2: Simple query with .keyword"
curl -X POST "https://localhost:9200/events-v2/_search" \
-u "${USERNAME}:${PASSWORD}" \
-k \
-H "Content-Type: application/json" \
-d '{
  "size": 1,
  "query": {
    "term": {
      "trace_id.keyword": "67a0ee088714f09f89d36047"
    }
  }
}'

echo -e "\n\n"

# Test 3: Check what fields are available in the index
echo "Test 3: Check index mapping"
curl -X GET "https://localhost:9200/events-v2/_mapping" \
-u "${USERNAME}:${PASSWORD}" \
-k \
-H "Content-Type: application/json"

echo -e "\n\n"

# Test 4: Full query without .keyword
echo "Test 4: Full query without .keyword"
curl -X POST "https://localhost:9200/events-v2/_search" \
-u "${USERNAME}:${PASSWORD}" \
-k \
-H "Content-Type: application/json" \
-d '{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        {
          "term": {
            "status": "succeeded"
          }
        },
        {
          "term": {
            "event_name": "handleMessageInThread_start"
          }
        },
        {
          "terms": {
            "trace_id": ["67a0ee088714f09f89d36047"]
          }
        }
      ]
    }
  },
  "aggs": {
    "user_events": {
      "terms": {
        "field": "trace_id",
        "size": 10000
      },
      "aggs": {
        "message_count": {
          "value_count": {
            "field": "_id"
          }
        }
      }
    }
  }
}'

echo -e "\n\n"

# Test 5: Full query with .keyword
echo "Test 5: Full query with .keyword"
curl -X POST "https://localhost:9200/events-v2/_search" \
-u "${USERNAME}:${PASSWORD}" \
-k \
-H "Content-Type: application/json" \
-d '{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        {
          "term": {
            "status.keyword": "succeeded"
          }
        },
        {
          "term": {
            "event_name.keyword": "handleMessageInThread_start"
          }
        },
        {
          "terms": {
            "trace_id.keyword": ["67a0ee088714f09f89d36047"]
          }
        }
      ]
    }
  },
  "aggs": {
    "user_events": {
      "terms": {
        "field": "trace_id.keyword",
        "size": 10000
      },
      "aggs": {
        "message_count": {
          "value_count": {
            "field": "_id"
          }
        }
      }
    }
  }
}'

echo -e "\n\n"

# Test 6: Check all available event_names
echo "Test 6: Check all available event_names"
curl -X POST "https://localhost:9200/events-v2/_search" \
-u "${USERNAME}:${PASSWORD}" \
-k \
-H "Content-Type: application/json" \
-d '{
  "size": 0,
  "aggs": {
    "event_names": {
      "terms": {
        "field": "event_name.keyword",
        "size": 100
      }
    }
  }
}'

echo -e "\n\nTests completed."