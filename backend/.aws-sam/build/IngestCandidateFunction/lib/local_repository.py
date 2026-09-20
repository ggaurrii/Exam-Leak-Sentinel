"""
local_repository.py

In-memory stand-in for dynamodb_client.py. Every function here matches
dynamodb_client.py's signature exactly (same args, same return shapes) so
handlers work completely unchanged regardless of which one is active —
see repository.py for the dispatch.

State lives in module-level dicts and resets whenever the process
restarts. That's fine for local dev/demo. Not meant for concurrent
production use — it's a placeholder for real DynamoDB, not a database.
"""

import copy
from typing import List, Optional

_exams: dict = {}
_feed_events: dict = {}
_alerts: dict = {}
_investigations: dict = {}


def _clone(item):
    return copy.deepcopy(item)


def reset():
    """Test/dev helper — clears all in-memory state."""
    _exams.clear()
    _feed_events.clear()
    _alerts.clear()
    _investigations.clear()


# --- Exams -------------------------------------------------------------

def put_exam(item: dict):
    _exams[item["exam_id"]] = _clone(item)


def get_exam(exam_id: str) -> Optional[dict]:
    item = _exams.get(exam_id)
    return _clone(item) if item else None


def list_exams() -> List[dict]:
    return [_clone(i) for i in _exams.values()]


# --- Feed events ---------------------------------------------------------

def put_feed_event(item: dict):
    _feed_events[item["event_id"]] = _clone(item)


def list_feed_events(exam_id: str) -> List[dict]:
    items = [i for i in _feed_events.values() if i["exam_id"] == exam_id]
    items.sort(key=lambda i: i.get("ingested_at", ""), reverse=True)
    return [_clone(i) for i in items]


def list_recent_feed_events(limit: int = 10) -> List[dict]:
    items = sorted(_feed_events.values(), key=lambda i: i.get("ingested_at", ""), reverse=True)
    return [_clone(i) for i in items[:limit]]


# --- Alerts ----------------------------------------------------------------

def put_alert(item: dict):
    _alerts[item["alert_id"]] = _clone(item)


def get_alert(alert_id: str) -> Optional[dict]:
    item = _alerts.get(alert_id)
    return _clone(item) if item else None


def list_alerts(risk_tier: Optional[str] = None) -> List[dict]:
    items = list(_alerts.values())
    if risk_tier:
        items = [i for i in items if i["risk_tier"] == risk_tier]
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return [_clone(i) for i in items]


def update_alert_review_status(alert_id: str, review_status: str):
    if alert_id in _alerts:
        _alerts[alert_id]["review_status"] = review_status


# --- Investigations -------------------------------------------------------

def put_investigation(item: dict):
    _investigations[item["investigation_id"]] = _clone(item)


def list_investigations(status: Optional[str] = None) -> List[dict]:
    items = list(_investigations.values())
    if status:
        items = [i for i in items if i["status"] == status]
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return [_clone(i) for i in items]
