# Exam Leak Sentinel — run it locally (verified working)

Both zips in this handoff were just tested end-to-end: exam registration,
synthetic feed, alerts, alert detail, monitoring, examinations, and
investigations all work against each other with zero AWS dependency.

## 1. Backend

```bash
unzip exam-leak-sentinel-backend-local-ready.zip -d backend
cd backend/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-local.txt
uvicorn local_server:app --reload --port 8000
```

Check it's alive: `curl http://localhost:8000/health` → `{"status":"ok"}`

No AWS credentials needed — `DATA_PROVIDER`, `EMBEDDING_PROVIDER`, and
`CLASSIFICATION_PROVIDER` all default to `"local"`.

## 2. Frontend

```bash
unzip exam-leak-sentinel-frontend-wired.zip -d frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — it redirects to `/overview`.
`.env.local` already points `NEXT_PUBLIC_API_BASE_URL` at
`http://localhost:8000`, so no config needed.

## 3. Try it

1. Go to **Examinations** → "Register exam" → fill title, date, a couple
   of reference questions (one per line) → Register.
2. Click **Run synthetic feed** on that exam's row — generates a mix of
   clean / partial / near-exact leak candidates and scores them.
3. Check **Alerts** — filter by High/Medium/Low.
4. Click into an alert — see the reference-vs-candidate comparison and
   the model trace.
5. **Monitoring** and **Investigations** reflect the same data.

## When AWS activates

- Backend: set `EMBEDDING_PROVIDER=bedrock` and
  `CLASSIFICATION_PROVIDER=bedrock` (plus the Bedrock model IDs) — no
  code changes, `matching_provider.py` just dispatches differently.
  Deploy the same handler files behind API Gateway.
- Frontend: change `NEXT_PUBLIC_API_BASE_URL` in `.env.local` to the
  real API Gateway URL. Nothing else changes.
