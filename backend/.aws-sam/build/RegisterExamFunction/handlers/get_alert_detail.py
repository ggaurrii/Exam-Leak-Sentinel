"""
GET /alerts/{alert_id}

Returns the full alert record: reference question text, candidate text,
similarity score, risk tier, explanation, and the matching-call trace
(model IDs + request IDs for both the embedding and classification
calls — "local-*" IDs when running the local provider, real Bedrock IDs
when running against Bedrock).
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
    alert_id = (event.get("pathParameters") or {}).get("alert_id")
    if not alert_id:
        return _response(400, {"error": "alert_id path parameter is required"})

    alert = repository.get_alert(alert_id)
    if not alert:
        return _response(404, {"error": f"Alert {alert_id} not found"})

    return _response(200, {
        "alert_id": alert["alert_id"],
        "exam_id": alert["exam_id"],
        "source_feed": alert["source_feed"],
        "review_status": alert["review_status"],
        "created_at": alert["created_at"],
        "detection": {
            "similarity_score": alert["similarity_score"],
            "risk_tier": alert["risk_tier"],
            "explanation": alert["explanation"],
        },
        "comparison": {
            "reference_question": alert["matched_question_text"],
            "candidate_text": alert["candidate_text"],
        },
        "bedrock_trace": {
            "embedding_model_id": alert["embedding_model_id"],
            "embedding_request_id": alert["embedding_request_id"],
            "classification_model_id": alert["classification_model_id"],
            "classification_request_id": alert["classification_request_id"],
        },
    })
