"""
GET /alerts?risk_tier=High

Query params:
  risk_tier (optional): "Low" | "Medium" | "High"
"""

import json

from lib import repository


def _response(status_code: int, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    risk_tier = params.get("risk_tier")

    if risk_tier and risk_tier not in ("Low", "Medium", "High"):
        return _response(400, {"error": "risk_tier must be Low, Medium, or High"})

    alerts = repository.list_alerts(risk_tier=risk_tier)

    # Trim candidate_text/explanation in the list view to keep payload light;
    # full detail is available via get_alert_detail.
    summary = [
        {
            "alert_id": a["alert_id"],
            "exam_id": a["exam_id"],
            "source_feed": a["source_feed"],
            "risk_tier": a["risk_tier"],
            "similarity_score": a["similarity_score"],
            "review_status": a["review_status"],
            "created_at": a["created_at"],
        }
        for a in alerts
    ]

    return _response(200, {"alerts": summary, "count": len(summary)})
