"""
bedrock_client.py

Thin, explicit wrapper around Amazon Bedrock's InvokeModel API.

Design constraints (from project spec — do not violate these):
  - This is the ONLY matching/classification path. There is no local
    embedding model, no TF-IDF, no scikit-learn cosine-similarity-on-
    bag-of-words fallback anywhere in this codebase.
  - Every call logs model_id, request latency, and a request id
    BEFORE returning, so a running Lambda's CloudWatch log is itself
    the demo proof that Bedrock was actually invoked.
  - If ENABLE_LOCAL_DEV_FALLBACK is not explicitly set to "true" in
    the environment, any Bedrock failure raises — it never silently
    degrades to a fake/local score. This is intentional: a silently
    degraded match score is worse than a loud failure for a system
    whose whole job is trustworthy exam-integrity signal.
"""

import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("exam_leak_sentinel.bedrock")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Config — model IDs are region-specific. Fill these in from the AWS console
# "Model access" page (exact strings, they vary by region/account).
# ---------------------------------------------------------------------------
TITAN_EMBED_MODEL_ID = os.environ.get(
    "TITAN_EMBED_MODEL_ID", "amazon.titan-embed-text-v1"
)
CLAUDE_MODEL_ID = os.environ.get(
    "CLAUDE_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))

# Explicit, off-by-default escape hatch. Must be the literal string "true".
# There is deliberately no code path that reads this to produce a fake
# embedding or classification — it exists only so a future local-dev mode
# could be added deliberately and visibly, not accidentally.
ENABLE_LOCAL_DEV_FALLBACK = os.environ.get("ENABLE_LOCAL_DEV_FALLBACK", "false").lower() == "true"

_bedrock_runtime = None


def _client():
    global _bedrock_runtime
    if _bedrock_runtime is None:
        _bedrock_runtime = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    return _bedrock_runtime


class BedrockInvocationError(RuntimeError):
    """Raised when a Bedrock call fails and no explicit fallback is enabled."""


@dataclass
class EmbeddingResult:
    vector: list
    model_id: str
    request_id: str
    latency_ms: float
    input_token_count: Optional[int] = None


@dataclass
class ClassificationResult:
    risk_tier: str          # "Low" | "Medium" | "High"
    explanation: str        # natural-language rationale
    model_id: str
    request_id: str
    latency_ms: float
    raw_response_text: str


def _log_invocation(kind: str, model_id: str, request_id: str, latency_ms: float, extra: dict = None):
    payload = {
        "event": "bedrock_invocation",
        "kind": kind,
        "model_id": model_id,
        "bedrock_request_id": request_id,
        "latency_ms": round(latency_ms, 1),
    }
    if extra:
        payload.update(extra)
    # Structured log line — this is what you screen-record for the demo.
    logger.info(json.dumps(payload))


def get_embedding(text: str) -> EmbeddingResult:
    """
    Calls Titan Text Embeddings (amazon.titan-embed-text-v1) and returns the
    vector. Raises BedrockInvocationError on failure unless
    ENABLE_LOCAL_DEV_FALLBACK=true, in which case the caller (not this
    function) is responsible for deciding what to do — this function still
    raises; it never fabricates a vector itself.
    """
    body = json.dumps({"inputText": text})
    started = time.time()
    try:
        response = _client().invoke_model(
            modelId=TITAN_EMBED_MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
    except ClientError as e:
        logger.error(json.dumps({
            "event": "bedrock_invocation_error",
            "kind": "embedding",
            "model_id": TITAN_EMBED_MODEL_ID,
            "error": str(e),
        }))
        raise BedrockInvocationError(f"Titan embedding call failed: {e}") from e

    latency_ms = (time.time() - started) * 1000
    request_id = response["ResponseMetadata"].get("RequestId", str(uuid.uuid4()))
    payload = json.loads(response["body"].read())

    _log_invocation(
        "embedding", TITAN_EMBED_MODEL_ID, request_id, latency_ms,
        extra={"input_chars": len(text)},
    )

    return EmbeddingResult(
        vector=payload["embedding"],
        model_id=TITAN_EMBED_MODEL_ID,
        request_id=request_id,
        latency_ms=latency_ms,
        input_token_count=payload.get("inputTextTokenCount"),
    )


def classify_match(
    reference_question: str,
    candidate_text: str,
    similarity_score: float,
    source_feed: str,
) -> ClassificationResult:
    """
    Calls a Bedrock-hosted Claude model to turn a raw similarity score into
    a human-readable explanation and a final risk tier. The numeric score
    is ONE input signal; Claude can upgrade/downgrade the tier the cosine
    score alone would imply (e.g. near-exact numeric similarity on a
    generic/boilerplate line is likely a false positive; a moderate score
    that reproduces a distinctive multi-part question stem is not).
    """
    system_prompt = (
        "You are an exam-integrity analyst. You are given a reference exam "
        "question, a piece of candidate content found on a monitored feed, "
        "and a cosine similarity score between their embeddings. Decide a "
        "risk tier of Low, Medium, or High for whether the candidate "
        "content represents a leak of the reference question, and give a "
        "one-to-two sentence explanation a human reviewer can act on. "
        "Respond ONLY with JSON in the form: "
        '{"risk_tier": "Low|Medium|High", "explanation": "..."}'
    )
    user_prompt = (
        f"Reference question:\n{reference_question}\n\n"
        f"Candidate content (source: {source_feed}):\n{candidate_text}\n\n"
        f"Cosine similarity score: {similarity_score:.4f}\n\n"
        "Classify the risk tier and explain your reasoning briefly."
    )

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 400,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    })

    started = time.time()
    try:
        response = _client().invoke_model(
            modelId=CLAUDE_MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
    except ClientError as e:
        logger.error(json.dumps({
            "event": "bedrock_invocation_error",
            "kind": "classification",
            "model_id": CLAUDE_MODEL_ID,
            "error": str(e),
        }))
        raise BedrockInvocationError(f"Bedrock Claude classification call failed: {e}") from e

    latency_ms = (time.time() - started) * 1000
    request_id = response["ResponseMetadata"].get("RequestId", str(uuid.uuid4()))
    payload = json.loads(response["body"].read())
    raw_text = "".join(
        block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"
    )

    _log_invocation(
        "classification", CLAUDE_MODEL_ID, request_id, latency_ms,
        extra={"similarity_score": round(similarity_score, 4), "source_feed": source_feed},
    )

    risk_tier, explanation = _parse_classification(raw_text, similarity_score)

    return ClassificationResult(
        risk_tier=risk_tier,
        explanation=explanation,
        model_id=CLAUDE_MODEL_ID,
        request_id=request_id,
        latency_ms=latency_ms,
        raw_response_text=raw_text,
    )


def _parse_classification(raw_text: str, similarity_score: float) -> tuple:
    """
    Parses Claude's JSON response. If parsing fails, this is a data-quality
    problem with the model output, not a Bedrock outage — we do NOT fall
    back to a local heuristic here either; we surface the raw text so a
    human reviewer sees exactly what came back, with a conservative
    "Medium" tier so it isn't silently dropped from the review queue.
    """
    try:
        parsed = json.loads(raw_text)
        tier = parsed["risk_tier"]
        if tier not in ("Low", "Medium", "High"):
            raise ValueError(f"Unexpected risk_tier value: {tier}")
        return tier, parsed["explanation"]
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(json.dumps({
            "event": "classification_parse_fallback",
            "reason": str(e),
            "raw_text": raw_text[:500],
        }))
        return "Medium", (
            "Model response could not be parsed as structured JSON; "
            f"flagged for manual review. Raw similarity score: {similarity_score:.4f}. "
            f"Raw model output: {raw_text[:300]}"
        )
