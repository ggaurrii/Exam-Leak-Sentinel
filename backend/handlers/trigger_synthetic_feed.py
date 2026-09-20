"""
POST /exams/{exam_id}/synthetic-feed

Body (optional): {"batch_size": 8}

Synchronous: generates a batch of synthetic candidate items (clean /
partial / near-exact leak mix, see lib/synthetic_feed.py) and runs every
one through the real matching pipeline (lib/ingestion.process_candidate —
the exact same path a real ingested candidate takes), then returns a
summary. This is what the Overview page's "Run synthetic feed" button
calls.

In the full architecture this becomes an EventBridge-scheduled tick into
Step Functions instead of a synchronous HTTP call; kept synchronous here
per the demo-deadline decision to prioritize an end-to-end working app
over the async orchestration.
"""

import json
import logging

from lib import repository, ingestion, synthetic_feed

logger = logging.getLogger("exam_leak_sentinel.trigger_synthetic_feed")
logger.setLevel(logging.INFO)

DEFAULT_BATCH_SIZE = 8


def _response(status_code: int, body):
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

    batch_size = body.get("batch_size", DEFAULT_BATCH_SIZE)

    exam = repository.get_exam(exam_id)
    if not exam:
        return _response(404, {"error": f"Exam {exam_id} not found"})

    reference_texts = [q["text"] for q in exam.get("reference_questions", [])]
    batch = synthetic_feed.generate_feed_batch(reference_texts, batch_size=batch_size)

    results = []
    tier_counts = {"Low": 0, "Medium": 0, "High": 0}
    for item in batch:
        result = ingestion.process_candidate(exam_id, item.candidate_text, item.source_feed)
        tier_counts[result["risk_tier"]] += 1
        results.append({
            **result,
            "source_feed": item.source_feed,
            "intended_category": item.intended_category,
        })

    logger.info(
        "Synthetic feed batch for exam %s: %d items, tier_counts=%s",
        exam_id, len(batch), tier_counts,
    )

    return _response(201, {
        "exam_id": exam_id,
        "batch_size": len(batch),
        "risk_tier_counts": tier_counts,
        "results": results,
    })
