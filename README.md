# Exam Leak Sentinel

**Examination integrity monitoring — catching leaked exam content before the exam starts, not after the scandal breaks.**

Live demo: https://exam-leak-sentinel-q4h8.vercel.app

## The problem

Exam paper leaks (NEET, UPSC, state boards) are a recurring, high-profile
problem in India. Today, leaks are only caught *after* the fact — through
manual tip-offs and post-hoc investigation. There's no real-time detection
layer that flags a leak while an exam window is still open.

## What it does

1. An institution registers an exam's reference questions.
2. A monitoring feed (synthetic, for demo purposes — designed to plug into
   real scraped sources) delivers candidate content from various "sources."
3. A matching engine scores each candidate against the reference paper using
   semantic similarity, classifying it **Low / Medium / High** risk with a
   human-readable explanation.
4. Flagged content lands in a review queue, showing the reference text and
   candidate text side by side as evidence.

## Architecture

**Frontend:** Next.js (App Router), deployed on Vercel.
Pages: Overview, Examinations, Monitoring, Alerts, Investigations.

**Backend:** AWS serverless stack, defined as code with AWS SAM
(`backend/template.yaml`):
- **7 Lambda functions** — register exam, list exams, ingest candidate,
  trigger synthetic feed, list alerts, get alert detail, list investigations
- **API Gateway (HTTP API)** — routes requests to the Lambda functions
- **DynamoDB** — 4 tables (Exams, Alerts, Investigations, FeedEvents) with
  GSIs for risk-tier, status, and exam-scoped queries

**Matching engine:** built around an explicit provider switch
(`lib/matching_provider.py`):
- **Primary path:** Amazon Bedrock — Titan Text Embeddings for semantic
  similarity, Claude for generating the risk explanation
- **Fallback path:** a local, transparently-labeled embedding + rule-based
  classifier (`lib/local_client.py`), used while Bedrock model access
  finishes enabling for this AWS account. It never silently pretends to be
  Bedrock — every response logs which provider actually ran and the
  real model ID (e.g. `local-hashing-tf-v1-dim512`).
- Switching between them is a two-line environment variable change
  (`EMBEDDING_PROVIDER`, `CLASSIFICATION_PROVIDER`), not a code rewrite.

## Running it locally

Backend:
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt -r requirements-local.txt
uvicorn local_server:app --reload --port 8000
```

Frontend:
```bash
npm install
npm run dev
```

See `RUN_LOCALLY.md` for more detail.

## Deploying the backend to AWS

```bash
cd backend
sam build
sam deploy --guided   # first time; use `sam deploy` after that
```

This provisions all 4 DynamoDB tables, 7 Lambda functions, and the API
Gateway HTTP API, and prints the API base URL as a stack output.

## Tech stack

Next.js, TypeScript, Python 3.11, AWS Lambda, API Gateway, DynamoDB, AWS SAM,
Amazon Bedrock (Titan Embed + Claude), Vercel.

## Built for

WeMakeDevs × AWS "First Commit" student hackathon.