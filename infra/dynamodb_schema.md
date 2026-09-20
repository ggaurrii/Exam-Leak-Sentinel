# DynamoDB Schema — Exam Leak Sentinel

All tables use on-demand (PAY_PER_REQUEST) billing for the demo — no
capacity planning needed. Env var names in `backend/lib/dynamodb_client.py`
map to these table names; override via Lambda environment variables per
stack (dev/staging/demo) if you want separate tables per environment.

## ExamLeakSentinel-Exams
| Attribute | Type | Notes |
|---|---|---|
| `exam_id` (PK) | String | UUID |
| `title` | String | |
| `scheduled_start` | String | ISO-8601 |
| `reference_questions` | List<Map> | `[{question_id, text, answer_options}]` |
| `reference_embeddings` | Map | `{question_id: [float, ...]}` — Titan vectors, cached at registration time |
| `created_at` | String | ISO-8601 |
| `status` | String | Active \| Completed \| Cancelled |

No GSI needed yet — exam count is small; list via scan for the
Examinations tab.

## ExamLeakSentinel-FeedEvents
| Attribute | Type | Notes |
|---|---|---|
| `event_id` (PK) | String | UUID |
| `exam_id` | String | |
| `source_feed` | String | "Public Feed A" \| "Public Feed B" \| "Institutional Feed" \| "Authorized Feed" |
| `candidate_text` | String | |
| `ingested_at` | String | ISO-8601 |
| `processed` | Bool | |

**GSI: ExamIndex** — PK `exam_id`, SK `ingested_at`. Powers "events today
for this exam" on the Overview dashboard.

## ExamLeakSentinel-Alerts
| Attribute | Type | Notes |
|---|---|---|
| `alert_id` (PK) | String | UUID |
| `exam_id` | String | |
| `event_id` | String | FK to FeedEvents |
| `source_feed` | String | |
| `matched_question_id` | String | |
| `matched_question_text` | String | denormalized for the detail view |
| `candidate_text` | String | denormalized for the detail view |
| `similarity_score` | Number | cosine similarity, 0-1 |
| `risk_tier` | String | Low \| Medium \| High |
| `explanation` | String | Bedrock Claude's natural-language rationale |
| `embedding_model_id` / `classification_model_id` | String | for the Bedrock trace panel |
| `embedding_request_id` / `classification_request_id` | String | for the Bedrock trace panel |
| `created_at` | String | ISO-8601 |
| `review_status` | String | Pending \| Reviewed |

**GSI: RiskTierIndex** — PK `risk_tier`, SK `created_at`. Powers the
filterable Alerts list view.

**GSI: ExamIndex** — PK `exam_id`, SK `created_at` (add if you need
per-exam alert history beyond what's shown via the app).

## ExamLeakSentinel-Investigations
| Attribute | Type | Notes |
|---|---|---|
| `investigation_id` (PK) | String | UUID |
| `alert_id` | String | FK to Alerts |
| `exam_id` | String | |
| `status` | String | Pending \| Reviewed |
| `reviewer_notes` | String | optional |
| `created_at` / `updated_at` | String | ISO-8601 |

**GSI: StatusIndex** — PK `status`, SK `created_at`. Powers the
Investigations review queue (Pending first, most recent first).

---

## AWS CLI to create these (example, us-east-1)

```bash
aws dynamodb create-table \
  --table-name ExamLeakSentinel-Exams \
  --attribute-definitions AttributeName=exam_id,AttributeType=S \
  --key-schema AttributeName=exam_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name ExamLeakSentinel-FeedEvents \
  --attribute-definitions \
      AttributeName=event_id,AttributeType=S \
      AttributeName=exam_id,AttributeType=S \
      AttributeName=ingested_at,AttributeType=S \
  --key-schema AttributeName=event_id,KeyType=HASH \
  --global-secondary-indexes \
    '[{"IndexName":"ExamIndex","KeySchema":[{"AttributeName":"exam_id","KeyType":"HASH"},{"AttributeName":"ingested_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name ExamLeakSentinel-Alerts \
  --attribute-definitions \
      AttributeName=alert_id,AttributeType=S \
      AttributeName=risk_tier,AttributeType=S \
      AttributeName=created_at,AttributeType=S \
  --key-schema AttributeName=alert_id,KeyType=HASH \
  --global-secondary-indexes \
    '[{"IndexName":"RiskTierIndex","KeySchema":[{"AttributeName":"risk_tier","KeyType":"HASH"},{"AttributeName":"created_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name ExamLeakSentinel-Investigations \
  --attribute-definitions \
      AttributeName=investigation_id,AttributeType=S \
      AttributeName=status,AttributeType=S \
      AttributeName=created_at,AttributeType=S \
  --key-schema AttributeName=investigation_id,KeyType=HASH \
  --global-secondary-indexes \
    '[{"IndexName":"StatusIndex","KeySchema":[{"AttributeName":"status","KeyType":"HASH"},{"AttributeName":"created_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
  --billing-mode PAY_PER_REQUEST
```
