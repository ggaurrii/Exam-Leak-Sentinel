"""
matching_engine.py

Orchestrates: embed reference questions (cached per exam) -> embed candidate
content -> cosine similarity against each reference question -> take the
best-matching question -> ask Bedrock Claude to classify + explain -> return
a MatchResult ready to be written as an Alert.

This module contains NO similarity computation other than plain cosine
similarity over Bedrock-produced vectors (pure math, not a competing
"local matching model"). The semantic understanding all comes from Bedrock.
"""

import logging
import math
from dataclasses import dataclass
from typing import List

from . import matching_provider as bedrock_client  # noqa: alias kept so
# call sites below (bedrock_client.get_embedding / .classify_match /
# .BedrockInvocationError) don't need to change — matching_provider
# re-exports BedrockInvocationError and dispatches to local_client or the
# real bedrock_client based on EMBEDDING_PROVIDER/CLASSIFICATION_PROVIDER.
# See matching_provider.py for the switch.

logger = logging.getLogger("exam_leak_sentinel.matching_engine")


@dataclass
class ReferenceQuestion:
    question_id: str
    text: str


@dataclass
class MatchResult:
    exam_id: str
    candidate_id: str
    source_feed: str
    matched_question_id: str
    matched_question_text: str
    candidate_text: str
    similarity_score: float
    risk_tier: str
    explanation: str
    embedding_model_id: str
    classification_model_id: str
    embedding_request_id: str
    classification_request_id: str
    total_latency_ms: float


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_reference_questions(questions: List[ReferenceQuestion]) -> dict:
    """
    Embeds each reference question once. Callers (the register-exam handler)
    should persist the resulting vectors (e.g. as a JSON blob in the exam's
    DynamoDB item) so ingest-time matching doesn't re-embed the whole paper
    on every candidate item.
    """
    embeddings = {}
    for q in questions:
        result = bedrock_client.get_embedding(q.text)
        embeddings[q.question_id] = result.vector
        logger.info(
            "Embedded reference question %s (%d dims, %.1fms)",
            q.question_id, len(result.vector), result.latency_ms,
        )
    return embeddings


# Score -> tier thresholds used ONLY as a pre-filter / sanity check before
# handing off to Claude for the real classification. Claude's classification
# is authoritative; these thresholds just decide whether it's even worth
# spending a classification call (see SIMILARITY_FLOOR below).
SIMILARITY_FLOOR = 0.35  # below this, skip Claude call entirely -> Low, no alert noise


def match_candidate_against_exam(
    exam_id: str,
    candidate_id: str,
    candidate_text: str,
    source_feed: str,
    reference_questions: List[ReferenceQuestion],
    reference_embeddings: dict,
) -> MatchResult:
    """
    reference_embeddings: {question_id: vector}, produced by
    embed_reference_questions() and stored on the exam record.
    """
    candidate_embedding = bedrock_client.get_embedding(candidate_text)

    best_question = None
    best_score = -1.0
    for q in reference_questions:
        vec = reference_embeddings.get(q.question_id)
        if vec is None:
            continue
        score = cosine_similarity(candidate_embedding.vector, vec)
        if score > best_score:
            best_score = score
            best_question = q

    if best_question is None:
        raise ValueError(f"No reference embeddings available for exam {exam_id}")

    total_latency = candidate_embedding.latency_ms

    if best_score < SIMILARITY_FLOOR:
        # Still a real Bedrock-backed decision (the embedding call happened),
        # just skips the extra Claude call for content that's clearly
        # unrelated -- saves cost/latency on the bulk of a synthetic feed
        # (mostly clean/unrelated posts) without inventing a local scorer.
        return MatchResult(
            exam_id=exam_id,
            candidate_id=candidate_id,
            source_feed=source_feed,
            matched_question_id=best_question.question_id,
            matched_question_text=best_question.text,
            candidate_text=candidate_text,
            similarity_score=best_score,
            risk_tier="Low",
            explanation=(
                f"Similarity to closest reference question ({best_score:.3f}) "
                f"is below the {SIMILARITY_FLOOR} floor; content appears unrelated."
            ),
            embedding_model_id=candidate_embedding.model_id,
            classification_model_id="(skipped — below similarity floor)",
            embedding_request_id=candidate_embedding.request_id,
            classification_request_id="",
            total_latency_ms=total_latency,
        )

    classification = bedrock_client.classify_match(
        reference_question=best_question.text,
        candidate_text=candidate_text,
        similarity_score=best_score,
        source_feed=source_feed,
    )
    total_latency += classification.latency_ms

    return MatchResult(
        exam_id=exam_id,
        candidate_id=candidate_id,
        source_feed=source_feed,
        matched_question_id=best_question.question_id,
        matched_question_text=best_question.text,
        candidate_text=candidate_text,
        similarity_score=best_score,
        risk_tier=classification.risk_tier,
        explanation=classification.explanation,
        embedding_model_id=candidate_embedding.model_id,
        classification_model_id=classification.model_id,
        embedding_request_id=candidate_embedding.request_id,
        classification_request_id=classification.request_id,
        total_latency_ms=total_latency,
    )
