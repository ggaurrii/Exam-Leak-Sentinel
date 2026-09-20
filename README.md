# Exam Leak Sentinel — backend / matching engine (first pass)

Real-time detection of leaked exam content: register a reference paper,
feed it candidate content from monitored sources, get a Bedrock-scored
risk tier + explanation per item, and review the results in an alerts /
investigations queue.

This pass covers the **backend + matching engine only** (frontend comes
next). Everything here is real code meant to run against a real AWS
account — nothing in this repo fabricates a Bedrock response.

## Matching provider: currently LOCAL, not Bedrock

For the demo deadline, `EMBEDDING_PROVIDER` and `CLASSIFICATION_PROVIDER`
are set to `"local"` by default (see `lib/matching_provider.py`). Matching
runs entirely offline — a deterministic hashing-trick lexical embedding
plus a rule-based risk classifier in `lib/local_client.py` — no Bedrock
calls, no AWS credentials needed for the matching step itself (DynamoDB
still needs real credentials).

This is a **deliberate, explicit switch**, not a silent fallback: whichever
provider is configured is the only one that runs, and every call is still
logged the same way (`local_invocation` instead of `bedrock_invocation` in
the structured log, so it's honestly distinguishable from a real Bedrock
call, never disguised as one).

**Trade-off you're accepting:** the local matcher is lexical (shared-
vocabulary based), not semantic. It catches near-exact and moderately
paraphrased leaks well (see `backend/smoke_test_embedding.py`... actually
see the inline test in this README below) but will miss a leak that's
reworded enough to share little exact wording with the reference question,
and can occasionally flag generic shared phrasing. Tune
`LOCAL_HIGH_THRESHOLD` / `LOCAL_MEDIUM_THRESHOLD` env vars if it's too
strict/loose for your demo content.

### Switching back to Bedrock later

Set both env vars to `"bedrock"`:
```bash
export EMBEDDING_PROVIDER=bedrock
export CLASSIFICATION_PROVIDER=bedrock
```
No code changes needed — `matching_engine.py` calls through
`matching_provider.py`, which dispatches to `bedrock_client.py` unchanged
from before. You'll still need Bedrock model access granted and
`TITAN_EMBED_MODEL_ID` / `CLAUDE_MODEL_ID` set (see the section below,
skip it entirely while running local).

## Layout

```
backend/
  lib/
    bedrock_client.py      # Titan embed + Claude classify, logged, no fallback
    matching_engine.py     # cosine similarity + orchestration
    models.py               # dataclasses mirroring DynamoDB item shapes
    dynamodb_client.py      # CRUD helpers over boto3's DynamoDB resource
    synthetic_feed.py       # clean / partial / near-exact leak generator
  handlers/
    register_exam.py        # POST /exams
    ingest_candidate.py      # POST /exams/{exam_id}/candidates
    list_alerts.py           # GET /alerts?risk_tier=High
    get_alert_detail.py      # GET /alerts/{alert_id}
    list_investigations.py   # GET /investigations?status=Pending
  smoke_test_embedding.py   # standalone Bedrock connectivity test
  requirements.txt
infra/
  dynamodb_schema.md        # table/GSI definitions + CLI to create them
```

## 1. Enable Bedrock model access (SKIP if running local — see above)

You need **Titan Text Embeddings** (`amazon.titan-embed-text-v1`) and a
**Claude model** (e.g. `anthropic.claude-3-5-sonnet-20241022-v2:0` — exact
ID varies by region) granted in your account. In the AWS Console: Bedrock
→ Model access → request both → wait for "Access granted". Copy the exact
model ID strings shown there — region-specific.

## 2. Configure credentials + env vars

Running local (current default) — you still need AWS credentials for
DynamoDB, just not for matching:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1

export EXAMS_TABLE=ExamLeakSentinel-Exams
export FEED_EVENTS_TABLE=ExamLeakSentinel-FeedEvents
export ALERTS_TABLE=ExamLeakSentinel-Alerts
export INVESTIGATIONS_TABLE=ExamLeakSentinel-Investigations

# EMBEDDING_PROVIDER / CLASSIFICATION_PROVIDER default to "local" — no
# need to set them unless you're switching back to Bedrock (see above).
```

If/when you switch back to Bedrock, also set:
```bash
export EMBEDDING_PROVIDER=bedrock
export CLASSIFICATION_PROVIDER=bedrock
export TITAN_EMBED_MODEL_ID=amazon.titan-embed-text-v1
export CLAUDE_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0   # your exact console ID
```

## 3. Smoke-test the matching path

```bash
cd backend
pip install -r requirements.txt
python smoke_test_embedding.py
```

Running local, this proves the hashing embedding + rule classifier behave
sanely (leak scores higher than unrelated content) with zero network
calls. Running Bedrock, this proves credentials/region/model IDs are
correct — the console output (request IDs, latencies, similarity scores)
is what to screen-record as "this is really Bedrock" in that mode.

## 4. Create the DynamoDB tables

See `infra/dynamodb_schema.md` for the schema and the exact `aws dynamodb
create-table` commands (4 tables, 2 with a GSI).

## 5. Run the handlers locally against real AWS

The handler files are plain `def handler(event, context)` functions —
Lambda's standard API Gateway proxy-integration shape — so you can invoke
them directly in a Python shell before wiring up API Gateway/SAM/CDK:

```python
import json
from handlers import register_exam

event = {
    "body": json.dumps({
        "title": "CS301 Midterm",
        "scheduled_start": "2026-10-02T09:00:00Z",
        "reference_questions": [
            {"question_id": "q1", "text": "Explain the difference between TCP and UDP..."}
        ],
    })
}
print(register_exam.handler(event, None))
```

Once you have an `exam_id` back, feed it candidates the same way via
`ingest_candidate.handler`, or generate a batch with
`lib.synthetic_feed.generate_feed_batch(reference_questions, batch_size=10)`
and loop over them.

## 6. Deploy

Not included yet in this pass (you asked to prioritize backend + matching
engine first). Next steps once you're ready: package each handler +
`lib/` for Lambda (SAM, CDK, or a zip + `aws lambda create-function`),
wire up API Gateway routes matching the paths in each handler's docstring,
and add the Step Functions state machine (ingest → embed → compare →
classify → write alert) plus an EventBridge rule to tick the synthetic
feed generator on a schedule.

## Constraint this code enforces

`bedrock_client.py` has no code path that produces a fake embedding or
classification. A Bedrock failure raises `BedrockInvocationError` and
propagates up as a 502 from the handler — it never silently degrades to a
local scorer. The one off-by-default flag (`ENABLE_LOCAL_DEV_FALLBACK`)
exists as a placeholder for a *future*, deliberately-added local dev mode;
right now nothing reads it to change behavior.
