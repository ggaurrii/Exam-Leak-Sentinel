// lib/api.ts
//
// Single point of contact with the backend. Every UI component calls
// through here — nothing fetches directly. Swapping in the final AWS API
// Gateway base URL later is a one-line env var change (see NEXT_PUBLIC_API_BASE_URL
// in .env.local) — no code here needs to change when that happens.
//
// STATUS OF THIS CONTRACT — all against the local FastAPI server
// (backend/local_server.py), which wraps the same handler functions that
// will run behind API Gateway:
//   - registerExam        -> POST /exams
//   - listExams            -> GET  /exams
//   - ingestCandidate       -> POST /exams/{exam_id}/candidates
//   - triggerSyntheticFeed  -> POST /exams/{exam_id}/synthetic-feed
//   - listAlerts            -> GET  /alerts?risk_tier=
//   - getAlertDetail        -> GET  /alerts/{alert_id}
//   - listInvestigations    -> GET  /investigations?status=
//
// No dedicated endpoints exist (or are planned) for overview stats,
// monitoring status, or a raw recent-events feed — those are composed
// client-side below from listExams + listAlerts + listInvestigations,
// which the backend already returns enough data to derive them from.

import type {
  RegisterExamRequest,
  RegisterExamResponse,
  IngestCandidateRequest,
  IngestCandidateResponse,
  ListAlertsResponse,
  AlertDetail,
  ListInvestigationsResponse,
  ListExamsResponse,
  ExamSummary,
  OverviewStats,
  MonitoringStatus,
  RecentEvent,
  RiskTier,
  ReviewStatus,
  SyntheticFeedResult,
} from "./types";

// Local dev default points at the FastAPI server started with
// `uvicorn local_server:app --port 8000`. Override via .env.local when
// pointing at a deployed API Gateway stage.
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(
      `Couldn't reach the backend at ${API_BASE_URL}${path}. Is local_server.py running (uvicorn local_server:app --port 8000)?`,
      0
    );
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(
      `Request to ${path} failed with ${res.status}: ${body}`,
      res.status
    );
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------
// Direct handler calls
// ---------------------------------------------------------------------

export function registerExam(
  body: RegisterExamRequest
): Promise<RegisterExamResponse> {
  return request<RegisterExamResponse>("/exams", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listExams(): Promise<ExamSummary[]> {
  const res = await request<ListExamsResponse>("/exams");
  return res.exams;
}

export function ingestCandidate(
  examId: string,
  body: IngestCandidateRequest
): Promise<IngestCandidateResponse> {
  return request<IngestCandidateResponse>(`/exams/${examId}/candidates`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function triggerSyntheticFeed(
  examId: string,
  batchSize: number = 10
): Promise<SyntheticFeedResult> {
  return request<SyntheticFeedResult>(`/exams/${examId}/synthetic-feed`, {
    method: "POST",
    body: JSON.stringify({ batch_size: batchSize }),
  });
}

export function listAlerts(riskTier?: RiskTier): Promise<ListAlertsResponse> {
  const qs = riskTier ? `?risk_tier=${riskTier}` : "";
  return request<ListAlertsResponse>(`/alerts${qs}`);
}

export function getAlertDetail(alertId: string): Promise<AlertDetail> {
  return request<AlertDetail>(`/alerts/${alertId}`);
}

export function listInvestigations(
  status?: ReviewStatus
): Promise<ListInvestigationsResponse> {
  const qs = status ? `?status=${status}` : "";
  return request<ListInvestigationsResponse>(`/investigations${qs}`);
}

// ---------------------------------------------------------------------
// Composed client-side — no dedicated backend endpoint for these; each
// is built from the confirmed calls above.
// ---------------------------------------------------------------------

export async function getOverviewStats(): Promise<OverviewStats> {
  const [exams, highAlerts, openReviews] = await Promise.all([
    listExams(),
    listAlerts("High"),
    listInvestigations("Pending"),
  ]);
  return {
    active_examinations: exams.filter((e) => e.monitoring_status === "Active")
      .length,
    events_today: exams.reduce((sum, e) => sum + e.events_today, 0),
    open_reviews: openReviews.count,
    high_risk_candidates: highAlerts.count,
  };
}

export async function getMonitoringStatus(
  examId: string
): Promise<MonitoringStatus> {
  const exams = await listExams();
  const exam = exams.find((e) => e.exam_id === examId) ?? null;
  const alerts = examId
    ? (await listAlerts()).alerts.filter((a) => a.exam_id === examId)
    : [];
  const sourceFeeds = new Set(alerts.map((a) => a.source_feed));
  return {
    is_live: exam?.monitoring_status === "Active",
    last_event_at: exam?.last_event_at ?? null,
    current_exam_id: exam?.exam_id ?? null,
    current_exam_title: exam?.title ?? null,
    permitted_source_count: sourceFeeds.size,
    events_today: exam?.events_today ?? 0,
    reviews_generated: exam?.investigations_total ?? 0,
  };
}

export async function getRecentEvents(
  limit: number = 10
): Promise<RecentEvent[]> {
  const { alerts } = await listAlerts();
  return alerts
    .slice()
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
    .slice(0, limit)
    .map((a) => ({
      event_id: a.alert_id,
      timestamp: a.created_at,
      source_feed: a.source_feed,
      description: `${a.risk_tier} risk match (similarity ${a.similarity_score.toFixed(
        2
      )}) — review status: ${a.review_status}`,
    }));
}
