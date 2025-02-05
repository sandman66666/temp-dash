"""
Analytics metrics API endpoints for user activity analysis
"""
from datetime import datetime, timezone, timedelta
from quart import Blueprint, jsonify, request, current_app
from quart_cors import cors

dub_metrics_bp = Blueprint('dub_metrics', __name__)
dub_metrics_bp = cors(dub_metrics_bp, allow_origin="*")

@dub_metrics_bp.route('/activity-users', methods=['POST'])
async def get_activity_users():
    """Get users based on their activity patterns"""
    try:
        data = await request.get_json()
        start_date = datetime.fromisoformat(data.get('startDate').replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(data.get('endDate').replace('Z', '+00:00'))
        filter_type = data.get('filterType')

        # Ensure dates are in UTC
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        current_app.logger.info(f"Fetching activity users with params: start={start_date}, end={end_date}, filter={filter_type}")

        # Build OpenSearch query based on filter type
        must_conditions = [
            {"range": {"timestamp": {
                "gte": int(start_date.timestamp() * 1000),
                "lte": int(end_date.timestamp() * 1000)
            }}}
        ]

        # Add filter for successful events only
        must_conditions.append({"term": {"status.keyword": "succeeded"}})

        # Build aggregation for user activity
        aggs = {
            "users": {
                "terms": {
                    "field": "trace_id.keyword",
                    "size": 10000
                },
                "aggs": {
                    "actions": {
                        "date_histogram": {
                            "field": "timestamp",
                            "calendar_interval": "day"
                        }
                    },
                    "first_action": {"min": {"field": "timestamp"}},
                    "last_action": {"max": {"field": "timestamp"}},
                    "user_email": {
                        "terms": {
                            "field": "email.keyword",
                            "size": 1
                        }
                    }
                }
            }
        }

        query = {
            "query": {"bool": {"must": must_conditions}},
            "aggs": aggs,
            "size": 0
        }

        # Execute query
        result = await current_app.analytics_service.opensearch.search(
            index=current_app.analytics_service.index,
            body=query
        )

        # Process results
        users = []
        for bucket in result["aggregations"]["users"]["buckets"]:
            user_id = bucket["key"]
            email = bucket["user_email"]["buckets"][0]["key"] if bucket["user_email"]["buckets"] else "Unknown"
            first_action = bucket["first_action"]["value"]
            last_action = bucket["last_action"]["value"]
            total_actions = bucket["doc_count"]
            days_between = (last_action - first_action) / (1000 * 60 * 60 * 24)  # Convert ms to days

            # Filter users based on activity pattern
            include_user = False
            if filter_type == "consecutive_days":
                # Check if user has actions on consecutive days
                action_dates = set(
                    datetime.fromtimestamp(hit["key"] / 1000, tz=timezone.utc).date()
                    for hit in bucket["actions"]["buckets"]
                )
                consecutive_days = any(
                    date + timedelta(days=1) in action_dates
                    for date in action_dates
                )
                include_user = consecutive_days
            elif filter_type == "one_to_two_weeks":
                include_user = 7 <= days_between <= 14
            elif filter_type == "two_to_three_weeks":
                include_user = 14 < days_between <= 21
            elif filter_type == "month_apart":
                include_user = days_between >= 28

            if include_user and total_actions >= 2:
                users.append({
                    "trace_id": user_id,
                    "email": email,
                    "firstAction": datetime.fromtimestamp(first_action / 1000, tz=timezone.utc).isoformat(),
                    "lastAction": datetime.fromtimestamp(last_action / 1000, tz=timezone.utc).isoformat(),
                    "daysBetween": round(days_between, 1),
                    "totalActions": total_actions
                })

        # Sort users by total actions descending
        users.sort(key=lambda x: x["totalActions"], reverse=True)

        return jsonify({
            "status": "success",
            "users": users,
            "timeRange": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error in get_activity_users: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

def init_app(app):
    """Initialize metrics blueprint with the app"""
    app.register_blueprint(dub_metrics_bp, url_prefix='/metrics')