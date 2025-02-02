# dashboardbackend/src/api/tasks.py
from quart import Blueprint, request, jsonify
import os
import logging
from opensearchpy import AsyncOpenSearch

logger = logging.getLogger(__name__)
tasks_bp = Blueprint('tasks', __name__)

def get_opensearch_client():
    opensearch_url = os.getenv('OPENSEARCH_URL', 'https://localhost:9200')
    client = AsyncOpenSearch(
         hosts=[opensearch_url],
         http_auth=(
             os.getenv('OPENSEARCH_USERNAME', 'elkadmin'),
             os.getenv('OPENSEARCH_PASSWORD', '')
         ),
         verify_certs=False  # Note: Set to True in production!
    )
    return client

@tasks_bp.route('/getTaskResults')
async def get_task_results():
    """
    Return drill‑down data based on a "metricId" parameter.
    
    - If a metricId is provided, filter events accordingly:
        • "sketch_users": events must have status "succeeded" and a sketchId.
        • "thread_users": events where event_name is "handleMessageInThread_start".
        • "render_users": events where event_name is "renderStart_end".
        • "active_chat_users" or "medium_chat_users": events where event_name is "handleMessageInThread_start".
    - If no metricId is provided, return distinct emails (only consider events that have an email field).
    """
    metric_id = request.args.get('metricId')
    client = get_opensearch_client()
    index = "events-v2"
    
    # Base query: events with status "succeeded"
    must_conditions = [{"term": {"status.keyword": "succeeded"}}]
    
    if metric_id:
        if metric_id == "sketch_users":
            must_conditions.append({"exists": {"field": "sketchId"}})
        elif metric_id == "thread_users":
            must_conditions.append({"term": {"event_name.keyword": "handleMessageInThread_start"}})
        elif metric_id == "render_users":
            must_conditions.append({"term": {"event_name.keyword": "renderStart_end"}})
        elif metric_id in ["active_chat_users", "medium_chat_users"]:
            must_conditions.append({"term": {"event_name.keyword": "handleMessageInThread_start"}})
        size = 1000
    else:
        # When no metricId is provided, require that email exists and use aggregation.
        must_conditions.append({"exists": {"field": "email"}})
        size = 0

    query = {
         "query": {
             "bool": {
                 "must": must_conditions
             }
         }
    }
    
    if not metric_id:
         query["aggs"] = {
              "distinct_emails": {
                   "terms": {"field": "email.keyword", "size": 1000}
              }
         }
    
    try:
         result = await client.search(index=index, body=query, size=size)
         if not metric_id:
              emails = [bucket["key"] for bucket in result["aggregations"]["distinct_emails"]["buckets"]]
              return jsonify({"emails": emails})
         else:
              events = []
              for hit in result["hits"]["hits"]:
                  source = hit["_source"]
                  events.append({
                      "email": source.get("email"),
                      "sketchId": source.get("sketchId"),
                      "timestamp": source.get("timestamp"),
                      "event_name": source.get("event_name")
                  })
              return jsonify({"events": events})
    except Exception as e:
         logger.error(f"Error in getTaskResults: {str(e)}", exc_info=True)
         return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getTaskStatus')
async def get_task_status():
    """
    Given a sketchId (via query parameter), return all production events that have a renderedAudioUrl and status "succeeded".
    """
    sketch_id = request.args.get('sketchId')
    if not sketch_id:
         return jsonify({"error": "sketchId parameter is required"}), 400

    client = get_opensearch_client()
    index = "events-v2"
    
    query = {
         "query": {
             "bool": {
                 "must": [
                     {"term": {"status.keyword": "succeeded"}},
                     {"term": {"sketchId.keyword": sketch_id}},
                     {"exists": {"field": "renderedAudioUrl"}}
                 ]
             }
         }
    }
    
    try:
         result = await client.search(index=index, body=query, size=1000)
         productions = []
         for hit in result["hits"]["hits"]:
              source = hit["_source"]
              productions.append({
                   "renderedAudioUrl": source.get("renderedAudioUrl"),
                   "timestamp": source.get("timestamp")
              })
         return jsonify({"productions": productions})
    except Exception as e:
         logger.error(f"Error in getTaskStatus: {str(e)}", exc_info=True)
         return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getUserEventsById')
async def get_user_events_by_id():
    """
    Given a userId from Descope (passed as 'userId' query parameter),
    return all events from OpenSearch for that user.
    This assumes that during ingestion you store the unique Descope user ID
    in the event under event_data.descopeUserId.
    """
    user_id = request.args.get('userId')
    if not user_id:
         return jsonify({"error": "userId parameter is required"}), 400

    client = get_opensearch_client()
    index = "events-v2"
    query = {
         "query": {
             "bool": {
                 "must": [
                     {"term": {"event_data.descopeUserId.keyword": user_id}},
                     {"term": {"status.keyword": "succeeded"}}
                 ]
             }
         },
         "size": 1000
    }
    try:
         result = await client.search(index=index, body=query)
         events = [hit["_source"] for hit in result["hits"]["hits"]]
         return jsonify({"events": events})
    except Exception as e:
         logger.error(f"Error in getUserEventsById: {str(e)}", exc_info=True)
         return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getGaugeUsers')
async def get_gauge_users():
    """
    Given a metricId (e.g., "sketch_users", "thread_users", etc.) as a query parameter,
    return a list of distinct user IDs (from event_data.descopeUserId) from OpenSearch for events
    that match the gauge criteria.
    """
    metric_id = request.args.get('metricId')
    if not metric_id:
         return jsonify({"error": "metricId parameter is required"}), 400

    client = get_opensearch_client()
    index = "events-v2"
    # Base query: events with status "succeeded" and that have a Descope user ID.
    must_conditions = [
         {"term": {"status.keyword": "succeeded"}},
         {"exists": {"field": "event_data.descopeUserId"}}
    ]

    if metric_id == "sketch_users":
        must_conditions.append({"exists": {"field": "sketchId"}})
    elif metric_id == "thread_users":
        must_conditions.append({"term": {"event_name.keyword": "handleMessageInThread_start"}})
    elif metric_id == "render_users":
        must_conditions.append({"term": {"event_name.keyword": "renderStart_end"}})
    elif metric_id in ["active_chat_users", "medium_chat_users"]:
        must_conditions.append({"term": {"event_name.keyword": "handleMessageInThread_start"}})
    
    query = {
         "query": {
             "bool": {
                 "must": must_conditions
             }
         },
         "aggs": {
              "distinct_users": {
                   "terms": {"field": "event_data.descopeUserId.keyword", "size": 1000}
              }
         },
         "size": 0
    }
    
    try:
         result = await client.search(index=index, body=query)
         user_ids = [bucket["key"] for bucket in result["aggregations"]["distinct_users"]["buckets"] if bucket["key"]]
         return jsonify({"userIds": user_ids})
    except Exception as e:
         logger.error(f"Error in getGaugeUsers: {str(e)}", exc_info=True)
         return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getGaugeUserCandidates')
async def get_gauge_user_candidates():
    """
    Given a metricId as a query parameter, this endpoint returns a list of distinct Descope user IDs
    from events that match the gauge criteria. It does this in two phases:
    
    1. It retrieves all user IDs from events with status "succeeded" and an existing user ID field.
    2. It uses a sub-aggregation (with a filter) to only include users that have at least one event
       meeting the gauge criteria.
    """
    metric_id = request.args.get('metricId')
    if not metric_id:
         return jsonify({"error": "metricId parameter is required"}), 400

    client = get_opensearch_client()
    index = "events-v2"
    
    # Base query: events with status "succeeded" and that have a Descope user ID.
    base_query = {
        "bool": {
            "must": [
                {"term": {"status.keyword": "succeeded"}},
                {"exists": {"field": "event_data.descopeUserId"}}
            ]
        }
    }
    
    # Define the gauge-specific filter.
    if metric_id == "sketch_users":
        gauge_filter = {"exists": {"field": "sketchId"}}
    elif metric_id == "thread_users":
        gauge_filter = {"term": {"event_name.keyword": "handleMessageInThread_start"}}
    elif metric_id == "render_users":
        gauge_filter = {"term": {"event_name.keyword": "renderStart_end"}}
    elif metric_id in ["active_chat_users", "medium_chat_users"]:
        gauge_filter = {"term": {"event_name.keyword": "handleMessageInThread_start"}}
    else:
        return jsonify({"error": "Invalid metricId"}), 400

    query = {
        "size": 0,
        "query": base_query,
        "aggs": {
            "users": {
                "terms": {
                    "field": "event_data.descopeUserId.keyword",
                    "size": 1000
                },
                "aggs": {
                    "gauge_events": {
                        "filter": {
                            "bool": {
                                "must": [gauge_filter]
                            }
                        }
                    },
                    "gauge_filter_bucket": {
                        "bucket_selector": {
                            "buckets_path": {"gaugeCount": "gauge_events._count"},
                            "script": "params.gaugeCount > 0"
                        }
                    }
                }
            }
        }
    }
    
    try:
        result = await client.search(index=index, body=query)
        user_candidates = [bucket["key"] for bucket in result["aggregations"]["users"]["buckets"]]
        return jsonify({"userIds": user_candidates})
    except Exception as e:
        logger.error(f"Error in getGaugeUserCandidates: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getFields')
async def get_fields():
    """
    Return a list of all top-level field names from the mapping of the "events-v2" index.
    """
    client = get_opensearch_client()
    index = "events-v2"
    try:
        mapping = await client.indices.get_mapping(index=index)
        properties = mapping.get(index, {}).get("mappings", {}).get("properties", {})
        fields = list(properties.keys())
        return jsonify({"fields": fields})
    except Exception as e:
        logger.error(f"Error in getFields: {str(e)}")
        return jsonify({"error": str(e)}), 500

def init_app(app):
    """Register tasks blueprint with the Quart app."""
    app.register_blueprint(tasks_bp)