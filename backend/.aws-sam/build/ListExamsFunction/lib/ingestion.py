"""
ingestion.py

The "process one candidate" sequence: load exam -> write FeedEvent ->
run matching_engine -> write Alert -> maybe write Investigation. Used by
both handlers/ingest_candidate.py (one item at a time, from a real feed)
and handlers/trigger_synthetic_feed.py (a batch at once, from the
synthetic generator) so the two don't duplicate this logic.
"""

import uuid
from datetime import datetime, timezone

from . import repository
from .matching_engine import ReferenceQuestion, match_candidate_against_exam


class ExamNotFoundError(ValueError):
    pass


def process_candidate(exam_id: str, candidate_text: str, source_feed: str) -> dict:
    """
    Returns: {event_id, alert_id, risk_tier, similarity_score, explanation}
    Raises: ExamNotFoundError, matching_provider.BedrockInvocationError
    """
    exam = repository.get_exam(exam_id)
    if not exam:
        raise ExamNotFoundError(f"Exam {exam_id} not found")

    reference_questions = [
        ReferenceQuestion(question_id=q["question_id"], text=q["text"])
        for q in exam["reference_questions"]
    ]
    reference_embeddings = exam["reference_embeddings"]

    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    repository.put_feed_event({
        "event_id": event_id,
        "exam_id": exam_id,
        "source_feed": source_feed,
        "candidate_text": candidate_text,
        "ingested_at": now,
        "processed": False,
    })

    match = match_candidate_against_exam(
        exam_id=exam_id,
        candidate_id=event_id,
        candidate_text=candidate_text,
        source_feed=source_feed,
        reference_questions=reference_questions,
        reference_embeddings=reference_embeddings,
    )

    alert_id = str(uuid.uuid4())
    repository.put_alert({
        "alert_id": alert_id,
        "exam_id": exam_id,
        "event_id": event_id,
        "source_feed": source_feed,
        "matched_question_id": match.matched_question_id,
        "matched_question_text": match.matched_question_text,
        "candidate_text": candidate_text,
        "similarity_score": match.similarity_score,
        "risk_tier": match.risk_tier,
        "explanation": match.explanation,
        "embedding_model_id": match.embedding_model_id,
        "classification_model_id": match.classification_model_id,
        "embedding_request_id": match.embedding_request_id,
        "classification_request_id": match.classification_request_id,
        "created_at": now,
        "review_status": "Pending",
    })

    if match.risk_tier in ("Medium", "High"):
        repository.put_investigation({
            "investigation_id": str(uuid.uuid4()),
            "alert_id": alert_id,
            "exam_id": exam_id,
            "status": "Pending",
            "created_at": now,
            "updated_at": now,
        })

    return {
        "event_id": event_id,
        "alert_id": alert_id,
        "risk_tier": match.risk_tier,
        "similarity_score": match.similarity_score,
        "explanation": match.explanation,
    }
