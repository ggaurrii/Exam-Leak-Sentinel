"""
POST /exams/{exam_id}/candidates

Body:
{
  "candidate_text": "...",
  "source_feed": "Public Feed A"
}

Thin adapter over lib/ingestion.py's process_candidate() — the actual
match -> write alert -> maybe write investigation sequence lives there so
this handler and trigger_synthetic_feed.py share it instead of
duplicating it.
"""

import json
import logging

from lib import ingestion, matching_provider

logger = logging.getLogger("exam_leak_sentinel.ingest_candidate")
logger.setLevel(logging.INFO)


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    exam_id = (event.get("pathParameters") or {}).get("exam_id")
    if not exam_id:
        return _response(400, {"error": "exam_id path parameter is required"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON body"})

    candidate_text = body.get("candidate_text")
    source_feed = body.get("source_feed", "Unknown Feed")

    if not candidate_text:
        return _response(400, {"error": "candidate_text is required"})

    try:
        result = ingestion.process_candidate(exam_id, candidate_text, source_feed)
    except ingestion.ExamNotFoundError as e:
        return _response(404, {"error": str(e)})
    except matching_provider.BedrockInvocationError as e:
        logger.error("Matching call failed during ingest for exam %s: %s", exam_id, e)
        return _response(502, {"error": f"Matching call failed: {e}"})

    logger.info(
        "Ingested candidate %s for exam %s -> risk_tier=%s score=%.4f (feed=%s)",
        result["event_id"], exam_id, result["risk_tier"], result["similarity_score"], source_feed,
    )

    return _response(201, result)
