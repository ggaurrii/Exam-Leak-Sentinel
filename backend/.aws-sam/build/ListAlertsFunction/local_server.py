"""
local_server.py

Thin FastAPI wrapper exposing the real Lambda handler functions over
localhost, so the frontend can be built and demoed against a fully
working backend before the AWS account is available. Handler logic is
NOT duplicated or rewritten here — every route builds an API-Gateway-
proxy-shaped `event` dict, calls the unmodified handler function, and
translates its {statusCode, body} return into an HTTP response. When the
AWS account activates, deployment means pointing real API Gateway routes
at these same handler functions — this file is dev tooling, it never
ships to Lambda.

Run:
    cd backend
    pip install -r requirements.txt -r requirements-local.txt
    uvicorn local_server:app --reload --port 8000

Data + matching both default to local (DATA_PROVIDER, EMBEDDING_PROVIDER,
CLASSIFICATION_PROVIDER all default to "local") — no AWS credentials
needed to run this server.
"""

import json
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from handlers import (
    register_exam,
    ingest_candidate,
    list_alerts,
    get_alert_detail,
    list_investigations,
    list_exams,
    trigger_synthetic_feed,
)

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

app = FastAPI(title="Exam Leak Sentinel — local dev API")

# Local dev only — wide open so the Next.js dev server (any localhost
# port) can call this without CORS friction. Do NOT carry this
# configuration into the real API Gateway deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _event_from_request(request: Request, path_params: Optional[dict] = None) -> dict:
    raw_body = await request.body()
    return {
        "body": raw_body.decode("utf-8") if raw_body else None,
        "pathParameters": path_params or None,
        "queryStringParameters": dict(request.query_params) or None,
    }


def _to_fastapi_response(handler_result: dict) -> JSONResponse:
    body = json.loads(handler_result["body"]) if handler_result.get("body") else None
    return JSONResponse(status_code=handler_result["statusCode"], content=body)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/exams")
async def route_register_exam(request: Request):
    event = await _event_from_request(request)
    return _to_fastapi_response(register_exam.handler(event, None))


@app.get("/exams")
async def route_list_exams(request: Request):
    event = await _event_from_request(request)
    return _to_fastapi_response(list_exams.handler(event, None))


@app.post("/exams/{exam_id}/candidates")
async def route_ingest_candidate(exam_id: str, request: Request):
    event = await _event_from_request(request, {"exam_id": exam_id})
    return _to_fastapi_response(ingest_candidate.handler(event, None))


@app.post("/exams/{exam_id}/synthetic-feed")
async def route_trigger_synthetic_feed(exam_id: str, request: Request):
    event = await _event_from_request(request, {"exam_id": exam_id})
    return _to_fastapi_response(trigger_synthetic_feed.handler(event, None))


@app.get("/alerts")
async def route_list_alerts(request: Request):
    event = await _event_from_request(request)
    return _to_fastapi_response(list_alerts.handler(event, None))


@app.get("/alerts/{alert_id}")
async def route_get_alert_detail(alert_id: str, request: Request):
    event = await _event_from_request(request, {"alert_id": alert_id})
    return _to_fastapi_response(get_alert_detail.handler(event, None))


@app.get("/investigations")
async def route_list_investigations(request: Request):
    event = await _event_from_request(request)
    return _to_fastapi_response(list_investigations.handler(event, None))
