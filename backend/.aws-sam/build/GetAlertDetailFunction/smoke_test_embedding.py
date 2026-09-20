"""
smoke_test_embedding.py

Standalone script proving the Bedrock Titan embedding call works end to
end against a real AWS account. Run this FIRST after setting up
credentials + model access, before deploying anything — it's the fastest
way to confirm your account/region/model-id combination is correct.

Usage:
    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_REGION=us-east-1              # wherever you enabled model access
    export TITAN_EMBED_MODEL_ID=amazon.titan-embed-text-v1
    python smoke_test_embedding.py

Prints: cosine similarity between a sample reference question and both a
near-exact leak and an unrelated sentence, plus the Bedrock request IDs
and latencies for both calls — this console output is what you'd screen-
record for the demo's "proof it's really calling Bedrock" moment.
"""

import sys

from lib import bedrock_client, matching_provider
from lib.matching_engine import cosine_similarity

SAMPLE_REFERENCE_QUESTION = (
    "Explain the difference between TCP and UDP, and give one real-world "
    "scenario where UDP is preferred despite being unreliable."
)

SAMPLE_LEAK_CANDIDATE = (
    "Q7: Explain the difference between TCP and UDP, and give one "
    "real-world scenario where UDP is preferred despite being unreliable. "
    "(leaked screenshot circulating in group chat)"
)

SAMPLE_UNRELATED_CANDIDATE = (
    "Does anyone know if the cafeteria near the exam hall is open before 8am?"
)


def main():
    print(f"Embedding provider: {matching_provider.EMBEDDING_PROVIDER}")
    print(f"Embedding model: {matching_provider.current_embedding_model_id()}")
    if matching_provider.EMBEDDING_PROVIDER == "bedrock":
        print(f"Region: {bedrock_client.BEDROCK_REGION}")
    print("-" * 70)

    try:
        ref = matching_provider.get_embedding(SAMPLE_REFERENCE_QUESTION)
        print(f"[OK] Reference embedded — {len(ref.vector)} dims, "
              f"request_id={ref.request_id}, latency={ref.latency_ms:.1f}ms")

        leak = matching_provider.get_embedding(SAMPLE_LEAK_CANDIDATE)
        print(f"[OK] Leak candidate embedded — request_id={leak.request_id}, "
              f"latency={leak.latency_ms:.1f}ms")

        unrelated = matching_provider.get_embedding(SAMPLE_UNRELATED_CANDIDATE)
        print(f"[OK] Unrelated candidate embedded — request_id={unrelated.request_id}, "
              f"latency={unrelated.latency_ms:.1f}ms")
    except matching_provider.BedrockInvocationError as e:
        print(f"[FAIL] Embedding call failed: {e}")
        if matching_provider.EMBEDDING_PROVIDER == "bedrock":
            print("Check: credentials, region, and that model access shows "
                  "'Access granted' on the Bedrock console's Model access page.")
        sys.exit(1)

    leak_score = cosine_similarity(ref.vector, leak.vector)
    unrelated_score = cosine_similarity(ref.vector, unrelated.vector)

    print("-" * 70)
    print(f"Cosine similarity, reference vs. near-exact leak:  {leak_score:.4f}")
    print(f"Cosine similarity, reference vs. unrelated post:   {unrelated_score:.4f}")
    print("-" * 70)

    if leak_score > unrelated_score:
        print("[PASS] Leak candidate scored higher than unrelated candidate, as expected.")
    else:
        print("[WARN] Leak candidate did NOT score higher than unrelated candidate — "
              "investigate before relying on this for the demo.")


if __name__ == "__main__":
    main()
