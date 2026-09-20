"""
POST /exams

Body:
{
  "title": "CS301 Midterm",
  "scheduled_start": "2026-10-02T09:00:00Z",
  "reference_questions": [
    {"question_id": "q1", "text": "...", "answer_options": ["A) ...", "B) ..."]},
    ...
  ]
}

Embeds every reference question (via whichever EMBEDDING_PROVIDER is
active — local or Bedrock, see lib/matching_provider.py) and stores the
resulting vectors on the exam item so ingest-time matching doesn't need
to re-embed the reference paper on every candidate.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from lib import repository, matching_provider
from lib.matching_engine import ReferenceQuestion, embed_reference_questions

logger = logging.getLogger("exam_leak_sentinel.register_exam")
logger.setLevel(logging.INFO)


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON body"})

    title = body.get("title")
    scheduled_start = body.get("scheduled_start")
    raw_questions = body.get("reference_questions")

    if not title or not scheduled_start or not raw_questions:
        return _response(400, {
            "error": "title, scheduled_start, and reference_questions are required"
        })

    questions = [
        ReferenceQuestion(question_id=q["question_id"], text=q["text"])
        for q in raw_questions
    ]

    try:
        embeddings = embed_reference_questions(questions)
    except matching_provider.BedrockInvocationError as e:
        logger.error("Embedding failed during exam registration: %s", e)
        return _response(502, {"error": f"Embedding call failed: {e}"})

    exam_id = str(uuid.uuid4())
    exam_item = {
        "exam_id": exam_id,
        "title": title,
        "scheduled_start": scheduled_start,
        "reference_questions": raw_questions,
        "reference_embeddings": embeddings,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "Active",
    }
    repository.put_exam(exam_item)

    logger.info("Registered exam %s (%s) with %d reference questions", exam_id, title, len(questions))

    return _response(201, {
        "exam_id": exam_id,
        "title": title,
        "question_count": len(questions),
        "embedding_model_id": matching_provider.current_embedding_model_id(),
    })
