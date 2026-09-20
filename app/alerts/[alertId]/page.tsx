"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, getAlertDetail } from "@/lib/api";
import type { AlertDetail } from "@/lib/types";
import { RiskBadge } from "@/components/RiskBadge";

export default function AlertDetailPage({
  params,
}: {
  params: { alertId: string };
}) {
  const [alert, setAlert] = useState<AlertDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAlertDetail(params.alertId)
      .then((data) => {
        if (!cancelled) {
          setAlert(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "Unexpected error loading this alert."
        );
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.alertId]);

  return (
    <main className="page">
      <div className="page-header" style={{ alignItems: "center" }}>
        <div>
          <div style={{ marginBottom: 4 }}>
            <Link href="/alerts" style={{ fontSize: 13 }}>
              ← All alerts
            </Link>
          </div>
          <h1 style={{ fontSize: 24 }}>
            Alert {params.alertId.slice(0, 8)}
          </h1>
        </div>
        {alert && (
          <RiskBadge tier={alert.detection.risk_tier} score={alert.detection.similarity_score} />
        )}
      </div>

      {loading && (
        <div className="card card-padded" style={{ color: "var(--color-text-muted)" }}>
          Loading…
        </div>
      )}
      {error && <div className="error-state">{error}</div>}

      {alert && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <section
            className="card card-padded"
            style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}
          >
            <Field label="Exam ID" value={alert.exam_id} mono />
            <Field label="Source feed" value={alert.source_feed} />
            <Field label="Review status" value={alert.review_status} />
            <Field
              label="Created"
              value={new Date(alert.created_at).toLocaleString()}
            />
          </section>

          <section>
            <h2 style={{ fontSize: 16, marginBottom: 10 }}>Detection</h2>
            <div className="card card-padded">
              <div style={{ marginBottom: 10, fontSize: 13 }}>
                <strong>Similarity score:</strong>{" "}
                {alert.detection.similarity_score.toFixed(3)}
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.6 }}>
                {alert.detection.explanation}
              </div>
            </div>
          </section>

          <section>
            <h2 style={{ fontSize: 16, marginBottom: 10 }}>
              Reference vs. candidate
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
              }}
            >
              <div className="card card-padded">
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--color-text-muted)",
                    marginBottom: 8,
                  }}
                >
                  Reference question
                </div>
                <div style={{ fontSize: 14, lineHeight: 1.6 }}>
                  {alert.comparison.reference_question}
                </div>
              </div>
              <div className="card card-padded">
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--color-text-muted)",
                    marginBottom: 8,
                  }}
                >
                  Candidate text (from {alert.source_feed})
                </div>
                <div style={{ fontSize: 14, lineHeight: 1.6 }}>
                  {alert.comparison.candidate_text}
                </div>
              </div>
            </div>
          </section>

          <section>
            <h2 style={{ fontSize: 16, marginBottom: 10 }}>Model trace</h2>
            <div className="card card-padded" style={{ fontSize: 13 }}>
              <table>
                <tbody>
                  <tr>
                    <td style={{ color: "var(--color-text-muted)", border: "none", padding: "4px 12px 4px 0" }}>
                      Embedding model
                    </td>
                    <td style={{ border: "none", padding: "4px 0", fontFamily: "monospace" }}>
                      {alert.bedrock_trace.embedding_model_id}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: "var(--color-text-muted)", border: "none", padding: "4px 12px 4px 0" }}>
                      Embedding request ID
                    </td>
                    <td style={{ border: "none", padding: "4px 0", fontFamily: "monospace" }}>
                      {alert.bedrock_trace.embedding_request_id}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: "var(--color-text-muted)", border: "none", padding: "4px 12px 4px 0" }}>
                      Classification model
                    </td>
                    <td style={{ border: "none", padding: "4px 0", fontFamily: "monospace" }}>
                      {alert.bedrock_trace.classification_model_id}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: "var(--color-text-muted)", border: "none", padding: "4px 12px 4px 0" }}>
                      Classification request ID
                    </td>
                    <td style={{ border: "none", padding: "4px 0", fontFamily: "monospace" }}>
                      {alert.bedrock_trace.classification_request_id}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 13, fontFamily: mono ? "monospace" : undefined }}>
        {value}
      </div>
    </div>
  );
}
