"""
local_client.py

Local, offline stand-ins for the Bedrock embedding + classification calls.
Pure stdlib — no numpy/scikit-learn, no network calls, no model download —
so a Lambda package built with this active stays tiny and deploys fast.
This exists because EMBEDDING_PROVIDER/CLASSIFICATION_PROVIDER were
switched to "local" for the deadline; see matching_provider.py for the
dispatch logic and README.md for how to switch back to Bedrock later.

Embedding: a hashing-trick bag-of-words vector. Each token is hashed
(deterministically, via hashlib — NOT Python's built-in hash(), which is
randomized per-process) into a fixed-size vector and accumulated by term
frequency. This needs no shared vocabulary/corpus fit step, so a reference
question embedded at registration time and a candidate embedded later
independently still land in the same vector space and are directly
comparable via cosine similarity — unlike a fitted TF-IDF vectorizer,
which would need the corpus available at both embed calls.

Classification: rule-based thresholds on the similarity score, with a
template-generated explanation that also reports literal token overlap
(for reviewer readability only — overlap count does NOT affect the score
or the tier, it's purely descriptive).

This is intentionally a lexical/statistical signal, not a semantic one —
it will miss paraphrased leaks that share little exact vocabulary with the
reference question, and it can occasionally over-trigger on generic
shared boilerplate. That trade-off is what you're accepting by running
without Bedrock for this pass.
"""

import hashlib
import json
import logging
import os
import re
import time
import uuid
from typing import List

from .bedrock_client import BedrockInvocationError, EmbeddingResult, ClassificationResult

logger = logging.getLogger("exam_leak_sentinel.local_client")
logger.setLevel(logging.INFO)

LOCAL_EMBEDDING_DIM = int(os.environ.get("LOCAL_EMBEDDING_DIM", "512"))
LOCAL_EMBED_MODEL_ID = f"local-hashing-tf-v1-dim{LOCAL_EMBEDDING_DIM}"
LOCAL_CLASSIFIER_MODEL_ID = "local-rule-classifier-v1"

# Tunable via env so thresholds can be adjusted without a redeploy of code.
LOCAL_HIGH_THRESHOLD = float(os.environ.get("LOCAL_HIGH_THRESHOLD", "0.70"))
LOCAL_MEDIUM_THRESHOLD = float(os.environ.get("LOCAL_MEDIUM_THRESHOLD", "0.45"))

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_index(token: str) -> int:
    # md5 is fine here — this is a bucket assignment, not a security
    # boundary. Deterministic across processes/Lambda invocations, unlike
    # Python's str hash().
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % LOCAL_EMBEDDING_DIM


def _log_invocation(kind: str, model_id: str, request_id: str, latency_ms: float, extra: dict = None):
    payload = {
        "event": "local_invocation",  # deliberately NOT "bedrock_invocation" — this is not a Bedrock call
        "kind": kind,
        "model_id": model_id,
        "request_id": request_id,
        "latency_ms": round(latency_ms, 2),
    }
    if extra:
        payload.update(extra)
    logger.info(json.dumps(payload))


def get_embedding(text: str) -> EmbeddingResult:
    started = time.time()
    vector = [0.0] * LOCAL_EMBEDDING_DIM
    tokens = _tokenize(text)
    for token in tokens:
        vector[_hash_index(token)] += 1.0

    latency_ms = (time.time() - started) * 1000
    request_id = f"local-{uuid.uuid4()}"

    _log_invocation(
        "embedding", LOCAL_EMBED_MODEL_ID, request_id, latency_ms,
        extra={"input_chars": len(text), "token_count": len(tokens)},
    )

    return EmbeddingResult(
        vector=vector,
        model_id=LOCAL_EMBED_MODEL_ID,
        request_id=request_id,
        latency_ms=latency_ms,
        input_token_count=len(tokens),
    )


def classify_match(
    reference_question: str,
    candidate_text: str,
    similarity_score: float,
    source_feed: str,
) -> ClassificationResult:
    started = time.time()

    if similarity_score >= LOCAL_HIGH_THRESHOLD:
        tier = "High"
    elif similarity_score >= LOCAL_MEDIUM_THRESHOLD:
        tier = "Medium"
    else:
        tier = "Low"

    ref_tokens = set(_tokenize(reference_question))
    cand_tokens = set(_tokenize(candidate_text))
    overlap = ref_tokens & cand_tokens
    # Drop very short/common tokens from the reported overlap so the
    # explanation highlights distinctive shared vocabulary, not "the",
    # "a", "is", etc. This filtering is cosmetic only (explanation text),
    # not part of the score.
    distinctive_overlap = sorted(t for t in overlap if len(t) > 3)[:8]

    if distinctive_overlap:
        overlap_str = ", ".join(f"'{t}'" for t in distinctive_overlap)
        explanation = (
            f"Local lexical similarity {similarity_score:.2f} ({tier} risk, "
            f"source: {source_feed}). Shares {len(distinctive_overlap)} distinctive "
            f"term(s) with the reference question: {overlap_str}."
        )
    else:
        explanation = (
            f"Local lexical similarity {similarity_score:.2f} ({tier} risk, "
            f"source: {source_feed}). No distinctive shared vocabulary found; "
            f"similarity is likely driven by common/structural words."
        )

    latency_ms = (time.time() - started) * 1000
    request_id = f"local-{uuid.uuid4()}"

    _log_invocation(
        "classification", LOCAL_CLASSIFIER_MODEL_ID, request_id, latency_ms,
        extra={"similarity_score": round(similarity_score, 4), "source_feed": source_feed, "risk_tier": tier},
    )

    return ClassificationResult(
        risk_tier=tier,
        explanation=explanation,
        model_id=LOCAL_CLASSIFIER_MODEL_ID,
        request_id=request_id,
        latency_ms=latency_ms,
        raw_response_text=explanation,
    )
