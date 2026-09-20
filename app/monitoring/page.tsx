"use client";

import { useEffect, useState } from "react";
import { ApiError, listExams, getRecentEvents } from "@/lib/api";
import type { ExamSummary, RecentEvent } from "@/lib/types";
import { StatCard } from "@/components/StatCard";

export default function MonitoringPage() {
  const [exams, setExams] = useState<ExamSummary[] | null>(null);
  const [events, setEvents] = useState<RecentEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([listExams(), getRecentEvents(15)])
      .then(([examData, eventData]) => {
        if (cancelled) return;
        setExams(examData);
        setEvents(eventData);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "Unexpected error loading monitoring data."
        );
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeExams = exams?.filter((e) => e.monitoring_status === "Active") ?? [];
  const totalEventsToday = exams?.reduce((s, e) => s + e.events_today, 0) ?? 0;
  const totalReviews = exams?.reduce((s, e) => s + e.investigations_total, 0) ?? 0;
  const sourceFeeds = new Set(events?.map((e) => e.source_feed));

  return (
    <main className="page">
      <div className="page-header">
        <h1 style={{ fontSize: 24 }}>Monitoring</h1>
      </div>

      {loading && (
        <div className="card card-padded" style={{ color: "var(--color-text-muted)", marginBottom: 20 }}>
          Loading…
        </div>
      )}
      {error && <div className="error-state" style={{ marginBottom: 20 }}>{error}</div>}

      {exams && (
        <>
          <section style={{ display: "flex", gap: 16, marginBottom: 24 }}>
            <StatCard label="Exams under monitoring" value={activeExams.length} />
            <StatCard label="Events today" value={totalEventsToday} />
            <StatCard label="Reviews generated" value={totalReviews} />
            <StatCard label="Distinct sources seen" value={sourceFeeds.size} />
          </section>

          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 16, marginBottom: 10 }}>Exam monitoring status</h2>
            <div className="card">
              {exams.length === 0 ? (
                <div className="empty-state">
                  No examinations registered. Register one from the Examinations tab
                  to start monitoring.
                </div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Exam</th>
                      <th>Status</th>
                      <th>Last event</th>
                      <th>Events today</th>
                      <th>Reviews generated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exams.map((e) => (
                      <tr key={e.exam_id}>
                        <td>{e.title}</td>
                        <td>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 6,
                            }}
                          >
                            <span
                              style={{
                                width: 7,
                                height: 7,
                                borderRadius: "50%",
                                display: "inline-block",
                                background:
                                  e.monitoring_status === "Active"
                                    ? "var(--color-risk-low)"
                                    : "var(--color-text-muted)",
                              }}
                            />
                            {e.monitoring_status}
                          </span>
                        </td>
                        <td>
                          {e.last_event_at
                            ? new Date(e.last_event_at).toLocaleString()
                            : "No events yet"}
                        </td>
                        <td>{e.events_today}</td>
                        <td>{e.investigations_total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          <section>
            <h2 style={{ fontSize: 16, marginBottom: 10 }}>Recent feed activity</h2>
            <div className="card">
              {!events || events.length === 0 ? (
                <div className="empty-state">
                  No feed events yet. Run the synthetic feed from an exam&apos;s row
                  on the Examinations tab.
                </div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Source</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((ev) => (
                      <tr key={ev.event_id}>
                        <td>{new Date(ev.timestamp).toLocaleString()}</td>
                        <td>{ev.source_feed}</td>
                        <td>{ev.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
