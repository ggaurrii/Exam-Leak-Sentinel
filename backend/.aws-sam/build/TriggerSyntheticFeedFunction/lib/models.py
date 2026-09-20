"""
models.py — plain dataclasses mirroring the DynamoDB item shapes.
See /infra/dynamodb_schema.md for table/index definitions.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ReferenceQuestionRecord:
    question_id: str
    text: str
    answer_options: List[str] = field(default_factory=list)


@dataclass
class Exam:
    exam_id: str
    title: str
    scheduled_start: str          # ISO-8601
    reference_questions: List[ReferenceQuestionRecord]
    reference_embeddings: dict    # {question_id: [float, ...]}
    s3_reference_key: Optional[str] = None
    created_at: Optional[str] = None
    status: str = "Active"        # Active | Completed | Cancelled


@dataclass
class FeedEvent:
    event_id: str
    exam_id: str
    source_feed: str              # e.g. "Public Feed A", "Institutional Feed"
    candidate_text: str
    ingested_at: str
    processed: bool = False


@dataclass
class Alert:
    alert_id: str
    exam_id: str
    event_id: str
    source_feed: str
    matched_question_id: str
    matched_question_text: str
    candidate_text: str
    similarity_score: float
    risk_tier: str                 # Low | Medium | High
    explanation: str
    embedding_model_id: str
    classification_model_id: str
    embedding_request_id: str
    classification_request_id: str
    created_at: str
    review_status: str = "Pending"  # Pending | Reviewed


@dataclass
class Investigation:
    investigation_id: str
    alert_id: str
    exam_id: str
    status: str = "Pending"        # Pending | Reviewed
    reviewer_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
