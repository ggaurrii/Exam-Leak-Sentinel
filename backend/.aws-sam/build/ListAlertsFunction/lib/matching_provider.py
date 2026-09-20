"""
matching_provider.py

Single dispatch point the matching engine calls through. Which
implementation actually runs is controlled by two env vars, checked
independently so you could (for example) run embeddings locally while
still using Bedrock Claude for classification, or vice versa:

    EMBEDDING_PROVIDER       = "local" | "bedrock"   (default: "local")
    CLASSIFICATION_PROVIDER  = "local" | "bedrock"   (default: "local")

This is an EXPLICIT switch, made deliberately for the demo deadline — not
a silent fallback. Nothing here catches a Bedrock failure and quietly
retries locally; whichever provider is configured is the only one that
runs, and if it fails, it fails loudly (BedrockInvocationError propagates
up exactly as before — local_client.py raises the same exception type for
symmetry, even though its failure modes are basically "your Python is
broken" rather than an AWS outage).

TO SWITCH BACK TO BEDROCK: set both env vars to "bedrock" (and make sure
TITAN_EMBED_MODEL_ID / CLAUDE_MODEL_ID / BEDROCK_REGION are set correctly,
see bedrock_client.py). No code changes needed.
"""

import os

from . import bedrock_client
from . import local_client
from .bedrock_client import BedrockInvocationError, EmbeddingResult, ClassificationResult  # re-exported

EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "local").lower()
CLASSIFICATION_PROVIDER = os.environ.get("CLASSIFICATION_PROVIDER", "local").lower()

_VALID = {"local", "bedrock"}
if EMBEDDING_PROVIDER not in _VALID:
    raise ValueError(f"EMBEDDING_PROVIDER must be 'local' or 'bedrock', got: {EMBEDDING_PROVIDER!r}")
if CLASSIFICATION_PROVIDER not in _VALID:
    raise ValueError(f"CLASSIFICATION_PROVIDER must be 'local' or 'bedrock', got: {CLASSIFICATION_PROVIDER!r}")


def current_embedding_model_id() -> str:
    """Reports whichever embedding model is actually configured to run —
    used by register_exam.py so its response doesn't hardcode Bedrock's
    Titan model ID regardless of provider."""
    if EMBEDDING_PROVIDER == "bedrock":
        return bedrock_client.TITAN_EMBED_MODEL_ID
    return local_client.LOCAL_EMBED_MODEL_ID


def get_embedding(text: str) -> EmbeddingResult:
    if EMBEDDING_PROVIDER == "bedrock":
        return bedrock_client.get_embedding(text)
    return local_client.get_embedding(text)


def classify_match(
    reference_question: str,
    candidate_text: str,
    similarity_score: float,
    source_feed: str,
) -> ClassificationResult:
    if CLASSIFICATION_PROVIDER == "bedrock":
        return bedrock_client.classify_match(
            reference_question=reference_question,
            candidate_text=candidate_text,
            similarity_score=similarity_score,
            source_feed=source_feed,
        )
    return local_client.classify_match(
        reference_question=reference_question,
        candidate_text=candidate_text,
        similarity_score=similarity_score,
        source_feed=source_feed,
    )
