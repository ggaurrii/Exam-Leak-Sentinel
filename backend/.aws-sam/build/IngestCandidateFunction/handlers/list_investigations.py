"""
GET /investigations?status=Pending

An investigation is created automatically for every Medium/High alert
(see lib/ingestion.py). This handler lists them most-recent-first,
optionally filtered by status.
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
    status = params.get("status")

    if status and status not in ("Pending", "Reviewed"):
        return _response(400, {"error": "status must be Pending or Reviewed"})

    investigations = repository.list_investigations(status=status)

    return _response(200, {
        "investigations": investigations,
        "count": len(investigations),
    })
