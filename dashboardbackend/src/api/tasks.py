from quart import Blueprint, request, jsonify
import os
import logging
from typing import Dict, List, Optional
from opensearchpy import AsyncOpenSearch
import aiohttp
import ssl
import dateutil.parser
import csv
import io
from datetime import datetime
from collections import defaultdict
import jwt
import asyncio
from opensearchpy.exceptions import ConnectionError, TransportError
from src.utils.query_builder import OpenSearchQueryBuilder

logger = logging.getLogger(__name__)
tasks_bp = Blueprint('tasks', __name__)

def get_opensearch_client():
    opensearch_url = os.getenv('OPENSEARCH_URL', 'https://localhost:9200')
    username = os.getenv('OPENSEARCH_USERNAME', 'elkadmin')
    password = os.getenv('OPENSEARCH_PASSWORD', '')
    
    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    client = AsyncOpenSearch(
        hosts=[opensearch_url],
        http_auth=(username, password),
        verify_certs=False,
        ssl_context=ssl_context,
        timeout=30
    )
    return client

async def fetch_descope_user_ids():
    """
    Fetch Descope users and return a list of v2userIds.
    We expect the Descope API to return a custom attribute (in customAttributes)
    called "v2UserId" that contains the OpenSearch user ID (a hex string matching trace_id).
    If not present, an empty list is returned.
    """
    descope_url = os.getenv('DESCOPE_API_URL')
    bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
    if not descope_url or not bearer_token:
        logger.error("Descope configuration missing.")
        return []
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        "projectId": "P2riizmYDJ2VAIjBw7ST0Qb2cNpd",
        "tenantIds": [],
        "text": "",
        "roleNames": [],
        "loginIds": [],
        "ssoAppIds": [],
        "customAttributes": {}
    }
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            async with session.post(descope_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Descope API response: {data}")
                    users = data.get('users', [])
                    # Retrieve the v2 user IDs from the custom attribute "v2UserId"
                    descope_ids = [
                        user.get('customAttributes', {}).get('v2UserId')
                        for user in users
                        if user.get('customAttributes', {}).get('v2UserId')
                    ]
                    logger.debug(f"Fetched {len(descope_ids)} Descope v2userIds")
                    return descope_ids
                else:
                    error_text = await response.text()
                    logger.error(f"Descope API error: {response.status} - {error_text}")
                    return []
    except Exception as e:
        logger.error(f"Exception while fetching Descope v2userIds: {str(e)}", exc_info=True)
        return []

@tasks_bp.route('/getGaugeUserCandidates')
async def get_gauge_user_candidates():
    metric_id = request.args.get('metricId')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    logger.info("getGaugeUserCandidates: metricId=%s, startDate=%s, endDate=%s", metric_id, start_date, end_date)
    
    if not metric_id:
        return jsonify({"error": "metricId parameter is required"}), 400

    # Fetch v2userIds from Descope
    descope_ids = await fetch_descope_user_ids()
    logger.info(f"Fetched {len(descope_ids)} Descope user IDs")
    if not descope_ids:
        logger.error("No Descope users found")
        return jsonify({"userIds": []})

    client = get_opensearch_client()
    index = "events-v2"
    query_builder = OpenSearchQueryBuilder()
    
    # Build base conditions
    must_conditions = [
        {"term": {"status.keyword": "succeeded"}},
        {"term": {"event_name.keyword": "handleMessageInThread_start"}},
        {"terms": {"trace_id.keyword": descope_ids}}
    ]
    
    # Add date range filter if provided
    if start_date and end_date:
        try:
            parsed_start = dateutil.parser.parse(start_date)
            parsed_end = dateutil.parser.parse(end_date)
            logger.debug("Parsed startDate: %s, endDate: %s", parsed_start.isoformat(), parsed_end.isoformat())
            must_conditions.append({
                "range": {
                    "timestamp": {
                        "gte": parsed_start.isoformat(),
                        "lte": parsed_end.isoformat()
                    }
                }
            })
        except Exception as parse_err:
            logger.error("Error parsing dates: %s", str(parse_err))
            await client.close()
            return jsonify({"error": "Invalid date format for startDate or endDate"}), 400

    # Build query using the same structure as analytics service
    query = query_builder.build_composite_query(
        must_conditions=must_conditions,
        aggregations={
            "aggs": {
                "thread_count": {
                    "terms": {"field": "trace_id.keyword", "size": 10000},
                    "aggs": {
                        "thread_filter": {
                            "bucket_selector": {
                                "buckets_path": {"count": "_count"},
                                "script": "params.count > 20" if metric_id in ["active_chat_users", "power_users"] else
                                         "params.count >= 5 && params.count <= 20" if metric_id == "medium_chat_users" else
                                         "params.count > 0"
                            }
                        }
                    }
                }
            }
        }
    )

    logger.debug("Final Query: %s", query)
    try:
        result = await client.search(index=index, body=query, size=0)
        await client.close()
        
        # Extract user IDs from buckets that passed the bucket selector
        user_ids = [bucket["key"] for bucket in result["aggregations"]["thread_count"]["buckets"]]
        logger.info("Found %d matching users", len(user_ids))
        
        return jsonify({"userIds": user_ids})
    except Exception as e:
        logger.error(f"Error in getGaugeUserCandidates: {str(e)}", exc_info=True)
        await client.close()
        return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getTaskResults')
async def get_task_results():
    metric_id = request.args.get('metricId')
    client = get_opensearch_client()
    index = "events-v2"
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
        must_conditions.append({"exists": {"field": "email"}})
        size = 0

    query = {"query": {"bool": {"must": must_conditions}}}
    if not metric_id:
        query["aggs"] = {"distinct_emails": {"terms": {"field": "email.keyword", "size": 1000}}}
    
    try:
        result = await client.search(index=index, body=query, size=size)
        await client.close()
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
        await client.close()
        return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getTaskStatus')
async def get_task_status():
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
        await client.close()
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
        await client.close()
        return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getUserEventsById')
async def get_user_events_by_id():
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({"error": "userId parameter is required"}), 400

    client = get_opensearch_client()
    index = "events-v2"
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"trace_id.keyword": user_id}},
                    {"term": {"status.keyword": "succeeded"}}
                ]
            }
        },
        "size": 1000
    }
    try:
        result = await client.search(index=index, body=query)
        await client.close()
        events = [hit["_source"] for hit in result["hits"]["hits"]]
        return jsonify({"events": events})
    except Exception as e:
        logger.error(f"Error in getUserEventsById: {str(e)}", exc_info=True)
        await client.close()
        return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getGaugeUsers')
async def get_gauge_users():
    metric_id = request.args.get('metricId')
    if not metric_id:
        return jsonify({"error": "metricId parameter is required"}), 400

    client = get_opensearch_client()
    index = "events-v2"
    must_conditions = [
        {"term": {"status.keyword": "succeeded"}},
        {"exists": {"field": "trace_id"}}
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
        "query": {"bool": {"must": must_conditions}},
        "aggs": {
            "distinct_users": {
                "terms": {
                    "field": "trace_id.keyword",
                    "size": 1000
                },
                "aggs": {
                    "user_email": {
                        "terms": {
                            "field": "email.keyword",
                            "size": 1
                        }
                    }
                }
            }
        },
        "size": 0
    }
    
    try:
        result = await client.search(index=index, body=query)
        await client.close()
        users = []
        for bucket in result["aggregations"]["distinct_users"]["buckets"]:
            if bucket["key"]:
                email_buckets = bucket["user_email"]["buckets"]
                email = email_buckets[0]["key"] if email_buckets else None
                users.append({
                    "userId": bucket["key"],
                    "email": email,
                    "count": bucket["doc_count"]
                })
        return jsonify({"users": users})
    except Exception as e:
        logger.error(f"Error in getGaugeUsers: {str(e)}", exc_info=True)
        await client.close()
        return jsonify({"error": str(e)}), 500

@tasks_bp.route('/getFields')
async def get_fields():
    client = get_opensearch_client()
    index = "events-v2"
    try:
        mapping = await client.indices.get_mapping(index=index)
        await client.close()
        properties = mapping.get(index, {}).get("mappings", {}).get("properties", {})
        fields = list(properties.keys())
        return jsonify({"fields": fields})
    except Exception as e:
        logger.error(f"Error in getFields: {str(e)}")
        await client.close()
        return jsonify({"error": str(e)}), 500

def init_app(app):
    """Register tasks blueprint with the Quart app."""
    app.register_blueprint(tasks_bp)

class EventDiscoveryService:
    def __init__(self, client: AsyncOpenSearch):
        self.client = client
        self.index = "events-v2"

    def _extract_user_id_from_token(self, auth_header: str) -> Optional[str]:
        """Extract user ID from JWT token."""
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get('sub')
        except Exception as e:
            logger.error(f"Error extracting user ID from token: {str(e)}")
            return None

    async def get_user_events(self, auth_header: str) -> Dict:
        """Get events for a user identified by their JWT token."""
        user_id = self._extract_user_id_from_token(auth_header)
        if not user_id:
            return {"error": "Invalid or missing authentication"}

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"trace_id.keyword": user_id}},
                        {"term": {"status.keyword": "succeeded"}}
                    ]
                }
            },
            "size": 1000
        }

        try:
            result = await self.client.search(index=self.index, body=query)
            events = [hit["_source"] for hit in result["hits"]["hits"]]
            return {"events": events}
        except Exception as e:
            logger.error(f"Error getting user events: {str(e)}")
            return {"error": str(e)}