"""
GET /exams

Lists registered exams with the derived fields the Examinations,
Monitoring, and Overview pages need — computed here so the frontend
doesn't need a separate raw-events endpoint:
  - question_count: len(reference_questions)
  - events_today: FeedEvents for this exam ingested today (UTC)
  - open_reviews: Pending investigations for this exam
  - investigations_total: all investigations ever created for this exam
    (used to derive "reviews generated" for the Monitoring tab)
  - last_event_at: timestamp of the most recent FeedEvent for this exam
    (used to derive a live/inactive monitoring indicator client-side)
  - monitoring_status: "Active" | "Inactive", mirrors the exam's status
"""

import json
from datetime import datetime, timezone

from lib import repository


def _response(status_code: int, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    exams = repository.list_exams()
    today = datetime.now(timezone.utc).date().isoformat()

    # Pulled once and filtered in-memory rather than once per exam.
    all_investigations = repository.list_investigations()

    summaries = []
    for exam in exams:
        exam_id = exam["exam_id"]
        feed_events = repository.list_feed_events(exam_id)
        events_today = sum(1 for e in feed_events if e.get("ingested_at", "").startswith(today))
        last_event_at = feed_events[0]["ingested_at"] if feed_events else None

        exam_investigations = [inv for inv in all_investigations if inv["exam_id"] == exam_id]
        open_reviews = sum(1 for inv in exam_investigations if inv["status"] == "Pending")

        summaries.append({
            "exam_id": exam_id,
            "title": exam["title"],
            "scheduled_start": exam["scheduled_start"],
            "question_count": len(exam.get("reference_questions", [])),
            "events_today": events_today,
            "open_reviews": open_reviews,
            "investigations_total": len(exam_investigations),
            "last_event_at": last_event_at,
            "monitoring_status": "Active" if exam.get("status") == "Active" else "Inactive",
        })

    return _response(200, {"exams": summaries, "count": len(summaries)})
