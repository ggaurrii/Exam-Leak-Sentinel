"""
dynamodb_client.py — thin CRUD helpers over boto3's DynamoDB resource.

Table names come from environment variables so the same code works across
dev/staging/demo stacks without edits. See /infra/dynamodb_schema.md for
the full schema (keys, GSIs, attribute types).
"""

import os
from decimal import Decimal
from typing import List, Optional

import boto3
from boto3.dynamodb.conditions import Key

_dynamodb = None


def _resource():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _dynamodb


EXAMS_TABLE = os.environ.get("EXAMS_TABLE", "ExamLeakSentinel-Exams")
FEED_EVENTS_TABLE = os.environ.get("FEED_EVENTS_TABLE", "ExamLeakSentinel-FeedEvents")
ALERTS_TABLE = os.environ.get("ALERTS_TABLE", "ExamLeakSentinel-Alerts")
INVESTIGATIONS_TABLE = os.environ.get("INVESTIGATIONS_TABLE", "ExamLeakSentinel-Investigations")


def _floats_to_decimal(obj):
    """DynamoDB's boto3 resource API rejects native floats — embeddings and
    similarity scores need conversion before put_item."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [_floats_to_decimal(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    return obj


def _decimals_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, list):
        return [_decimals_to_float(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _decimals_to_float(v) for k, v in obj.items()}
    return obj


# --- Exams -------------------------------------------------------------

def put_exam(item: dict):
    table = _resource().Table(EXAMS_TABLE)
    table.put_item(Item=_floats_to_decimal(item))


def get_exam(exam_id: str) -> Optional[dict]:
    table = _resource().Table(EXAMS_TABLE)
    resp = table.get_item(Key={"exam_id": exam_id})
    item = resp.get("Item")
    return _decimals_to_float(item) if item else None


def list_exams() -> List[dict]:
    table = _resource().Table(EXAMS_TABLE)
    items = []
    resp = table.scan()
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    return [_decimals_to_float(i) for i in items]


# --- Feed events ---------------------------------------------------------

def put_feed_event(item: dict):
    table = _resource().Table(FEED_EVENTS_TABLE)
    table.put_item(Item=_floats_to_decimal(item))


def list_feed_events(exam_id: str) -> List[dict]:
    """Requires the ExamIndex GSI (exam_id HASH, ingested_at RANGE) — see
    infra/dynamodb_schema.md."""
    table = _resource().Table(FEED_EVENTS_TABLE)
    resp = table.query(
        IndexName="ExamIndex",
        KeyConditionExpression=Key("exam_id").eq(exam_id),
        ScanIndexForward=False,
    )
    return [_decimals_to_float(i) for i in resp.get("Items", [])]


def list_recent_feed_events(limit: int = 10) -> List[dict]:
    """No dedicated index for this — scans and sorts client-side. Fine at
    demo scale; revisit with a GSI on a constant partition key +
    ingested_at if this table grows large."""
    table = _resource().Table(FEED_EVENTS_TABLE)
    items = []
    resp = table.scan()
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    items.sort(key=lambda i: i.get("ingested_at", ""), reverse=True)
    return [_decimals_to_float(i) for i in items[:limit]]


# --- Alerts ----------------------------------------------------------------

def put_alert(item: dict):
    table = _resource().Table(ALERTS_TABLE)
    table.put_item(Item=_floats_to_decimal(item))


def get_alert(alert_id: str) -> Optional[dict]:
    table = _resource().Table(ALERTS_TABLE)
    resp = table.get_item(Key={"alert_id": alert_id})
    item = resp.get("Item")
    return _decimals_to_float(item) if item else None


def list_alerts(risk_tier: Optional[str] = None) -> List[dict]:
    table = _resource().Table(ALERTS_TABLE)
    if risk_tier:
        # Requires a GSI: risk_tier (PK) + created_at (SK) — see schema doc.
        resp = table.query(
            IndexName="RiskTierIndex",
            KeyConditionExpression=Key("risk_tier").eq(risk_tier),
            ScanIndexForward=False,
        )
        return [_decimals_to_float(i) for i in resp.get("Items", [])]
    resp = table.scan()
    items = resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return [_decimals_to_float(i) for i in items]


def update_alert_review_status(alert_id: str, review_status: str):
    table = _resource().Table(ALERTS_TABLE)
    table.update_item(
        Key={"alert_id": alert_id},
        UpdateExpression="SET review_status = :s",
        ExpressionAttributeValues={":s": review_status},
    )


# --- Investigations -------------------------------------------------------

def put_investigation(item: dict):
    table = _resource().Table(INVESTIGATIONS_TABLE)
    table.put_item(Item=_floats_to_decimal(item))


def list_investigations(status: Optional[str] = None) -> List[dict]:
    table = _resource().Table(INVESTIGATIONS_TABLE)
    if status:
        # Requires a GSI: status (PK) + created_at (SK) — see schema doc.
        resp = table.query(
            IndexName="StatusIndex",
            KeyConditionExpression=Key("status").eq(status),
            ScanIndexForward=False,
        )
        return [_decimals_to_float(i) for i in resp.get("Items", [])]
    resp = table.scan()
    items = resp.get("Items", [])
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return [_decimals_to_float(i) for i in items]
