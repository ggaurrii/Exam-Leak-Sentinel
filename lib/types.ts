// lib/types.ts
//
// Types for the pieces of the API contract that are CONFIRMED — they mirror
// the actual Lambda handler request/response shapes in the backend repo
// (backend/handlers/*.py) as of this pass. Anything not confirmed against a
// real handler is marked TODO in api.ts, not guessed here.

export type RiskTier = "Low" | "Medium" | "High";
export type ReviewStatus = "Pending" | "Reviewed";

export interface ReferenceQuestionInput {
  question_id: string;
  text: string;
  answer_options?: string[];
}

export interface RegisterExamRequest {
  title: string;
  scheduled_start: string; // ISO-8601
  reference_questions: ReferenceQuestionInput[];
}

export interface RegisterExamResponse {
  exam_id: string;
  title: string;
  question_count: number;
  embedding_model_id: string;
}

export interface ListExamsResponse {
  exams: ExamSummary[];
  count: number;
}

export interface IngestCandidateRequest {
  candidate_text: string;
  source_feed: string;
}

export interface IngestCandidateResponse {
  event_id: string;
  alert_id: string;
  risk_tier: RiskTier;
  similarity_score: number;
  explanation: string;
}

export interface AlertSummary {
  alert_id: string;
  exam_id: string;
  source_feed: string;
  risk_tier: RiskTier;
  similarity_score: number;
  review_status: ReviewStatus;
  created_at: string;
}

export interface ListAlertsResponse {
  alerts: AlertSummary[];
  count: number;
}

export interface AlertDetail {
  alert_id: string;
  exam_id: string;
  source_feed: string;
  review_status: ReviewStatus;
  created_at: string;
  detection: {
    similarity_score: number;
    risk_tier: RiskTier;
    explanation: string;
  };
  comparison: {
    reference_question: string;
    candidate_text: string;
  };
  bedrock_trace: {
    embedding_model_id: string;
    embedding_request_id: string;
    classification_model_id: string;
    classification_request_id: string;
  };
}

export interface Investigation {
  investigation_id: string;
  alert_id: string;
  exam_id: string;
  status: ReviewStatus;
  reviewer_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ListInvestigationsResponse {
  investigations: Investigation[];
  count: number;
}

// --- NOT YET BACKED BY A HANDLER — shapes below are provisional. See the
// "Open questions" note in api.ts. Do not treat these as confirmed. ---

export interface ExamSummary {
  exam_id: string;
  title: string;
  scheduled_start: string;
  question_count: number;
  events_today: number;
  open_reviews: number;
  investigations_total: number;
  last_event_at: string | null;
  monitoring_status: "Active" | "Inactive";
}

export interface SyntheticFeedResult {
  exam_id: string;
  batch_size: number;
  risk_tier_counts: Record<RiskTier, number>;
  results: {
    event_id: string;
    alert_id: string;
    risk_tier: RiskTier;
    similarity_score: number;
    explanation: string;
    source_feed: string;
    intended_category: string;
  }[];
}

export interface OverviewStats {
  active_examinations: number;
  events_today: number;
  open_reviews: number;
  high_risk_candidates: number;
}

export interface MonitoringStatus {
  is_live: boolean;
  last_event_at: string | null;
  current_exam_id: string | null;
  current_exam_title: string | null;
  permitted_source_count: number;
  events_today: number;
  reviews_generated: number;
}

export interface RecentEvent {
  event_id: string;
  timestamp: string;
  source_feed: string;
  description: string;
}
