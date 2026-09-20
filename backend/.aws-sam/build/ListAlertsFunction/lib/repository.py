"""
repository.py

Single dispatch point every handler goes through for data access —
mirrors matching_provider.py's pattern exactly. Which store actually runs
is controlled by:

    DATA_PROVIDER = "local" | "dynamodb"   (default: "local")

"local" -> local_repository.py (in-memory, no AWS needed)
"dynamodb" -> dynamodb_client.py (real AWS, unchanged from before)

Both modules expose the identical function set with identical signatures,
so this file is a thin passthrough — swapping providers is one env var,
never a code change in the handlers or in either backing module.
"""

import os
from typing import List, Optional

from . import dynamodb_client
from . import local_repository

DATA_PROVIDER = os.environ.get("DATA_PROVIDER", "local").lower()

_VALID = {"local", "dynamodb"}
if DATA_PROVIDER not in _VALID:
    raise ValueError(f"DATA_PROVIDER must be 'local' or 'dynamodb', got: {DATA_PROVIDER!r}")

_impl = local_repository if DATA_PROVIDER == "local" else dynamodb_client


def put_exam(item: dict):
    return _impl.put_exam(item)


def get_exam(exam_id: str) -> Optional[dict]:
    return _impl.get_exam(exam_id)


def list_exams() -> List[dict]:
    return _impl.list_exams()


def put_feed_event(item: dict):
    return _impl.put_feed_event(item)


def list_feed_events(exam_id: str) -> List[dict]:
    return _impl.list_feed_events(exam_id)


def list_recent_feed_events(limit: int = 10) -> List[dict]:
    return _impl.list_recent_feed_events(limit)


def put_alert(item: dict):
    return _impl.put_alert(item)


def get_alert(alert_id: str) -> Optional[dict]:
    return _impl.get_alert(alert_id)


def list_alerts(risk_tier: Optional[str] = None) -> List[dict]:
    return _impl.list_alerts(risk_tier=risk_tier)


def update_alert_review_status(alert_id: str, review_status: str):
    return _impl.update_alert_review_status(alert_id, review_status)


def put_investigation(item: dict):
    return _impl.put_investigation(item)


def list_investigations(status: Optional[str] = None) -> List[dict]:
    return _impl.list_investigations(status=status)
