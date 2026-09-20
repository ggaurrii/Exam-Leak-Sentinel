"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  getOverviewStats,
  listExams,
  listInvestigations,
  getRecentEvents,
  triggerSyntheticFeed,
} from "@/lib/api";
import type {
  ExamSummary,
  Investigation,
  OverviewStats,
  RecentEvent,
} from "@/lib/types";
import { StatCard } from "@/components/StatCard";
import Link from "next/link";

interface LoadState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

function useApiCall<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<LoadState<T>>({
    data: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, error: null, loading: true });
    fn()
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError ? err.message : "Unexpected error loading data.";
        setState({ data: null, error: message, loading: false });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}

export default function OverviewPage() {
  const stats = useApiCall<OverviewStats>(getOverviewStats);
  const exams = useApiCall<ExamSummary[]>(listExams);
  const openReviews = useApiCall(() => listInvestigations("Pending"));
  const recentEvents = useApiCall<RecentEvent[]>(() => getRecentEvents(8));

  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  const currentExam = exams.data?.[0] ?? null;

  async function handleRunSyntheticFeed() {
    if (!currentExam) return;
    setTriggering(true);
    setTriggerError(null);
    try {
      await triggerSyntheticFeed(currentExam.exam_id, 10);
    } catch (err) {
      setTriggerError(
        err instanceof ApiError ? err.message : "Failed to trigger synthetic feed."
      );
    } finally {
      setTriggering(false);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <h1 style={{ fontSize: 24 }}>Overview</h1>
        <button
          className="btn-primary"
          onClick={handleRunSyntheticFeed}
          disabled={triggering || !currentExam}
          title={
            !currentExam
              ? "No active examination to run the synthetic feed against"
              : undefined
          }
        >
          {triggering ? "Running synthetic feed…" : "Run synthetic feed"}
        </button>
      </div>

      {triggerError && (
        <div className="error-state" style={{ marginBottom: 16 }}>
          {triggerError}
        </div>
      )}

      <section style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        {stats.loading && <StatsSkeleton />}
        {stats.error && (
          <div className="error-state" style={{ flex: 1 }}>
            Couldn&apos;t load overview stats: {stats.error}
          </div>
        )}
        {stats.data && (
          <>
            <StatCard label="Active examinations" value={stats.data.active_examinations} />
            <StatCard label="Events today" value={stats.data.events_today} />
            <StatCard label="Open reviews" value={stats.data.open_reviews} />
            <StatCard label="High-risk candidates" value={stats.data.high_risk_candidates} />
          </>
        )}
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Current examination</h2>
        <div className="card card-padded">
          {exams.loading && <p style={{ color: "var(--color-text-muted)" }}>Loading…</p>}
          {exams.error && (
            <div className="error-state">
              Couldn&apos;t load examinations: {exams.error}
            </div>
          )}
          {exams.data && exams.data.length === 0 && (
            <div className="empty-state">
              No examinations registered yet. Register one to start monitoring.
            </div>
          )}
          {currentExam && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontFamily: "var(--font-serif)", fontSize: 18, marginBottom: 4 }}>
                  {currentExam.title}
                </div>
                <div style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
                  Scheduled {new Date(currentExam.scheduled_start).toLocaleString()} ·{" "}
                  {currentExam.question_count} reference questions
                </div>
              </div>
              <div style={{ display: "flex", gap: 24, fontSize: 13, textAlign: "right" }}>
                <div>
                  <div style={{ color: "var(--color-text-muted)" }}>Events today</div>
                  <div style={{ fontSize: 16 }}>{currentExam.events_today}</div>
                </div>
                <div>
                  <div style={{ color: "var(--color-text-muted)" }}>Open reviews</div>
                  <div style={{ fontSize: 16 }}>{currentExam.open_reviews}</div>
                </div>
                <Link href="/examinations">View examinations</Link>
              </div>
            </div>
          )}
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
            <h2 style={{ fontSize: 16 }}>Open reviews</h2>
            <Link href="/investigations" style={{ fontSize: 13 }}>
              View all
            </Link>
          </div>
          <div className="card">
            {openReviews.loading && (
              <div style={{ padding: 20, color: "var(--color-text-muted)" }}>Loading…</div>
            )}
            {openReviews.error && (
              <div className="error-state" style={{ margin: 16 }}>
                Couldn&apos;t load open reviews: {openReviews.error}
              </div>
            )}
            {openReviews.data && openReviews.data.investigations.length === 0 && (
              <div className="empty-state">No open reviews right now.</div>
            )}
            {openReviews.data && openReviews.data.investigations.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>Investigation</th>
                    <th>Status</th>
                    <th>Opened</th>
                  </tr>
                </thead>
                <tbody>
                  {openReviews.data.investigations.slice(0, 5).map((inv: Investigation) => (
                    <tr key={inv.investigation_id}>
                      <td>
                        <Link href={`/alerts/${inv.alert_id}`}>{inv.investigation_id.slice(0, 8)}</Link>
                      </td>
                      <td>{inv.status}</td>
                      <td>{new Date(inv.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>Recent activity</h2>
          <div className="card card-padded">
            {recentEvents.loading && <p style={{ color: "var(--color-text-muted)" }}>Loading…</p>}
            {recentEvents.error && (
              <div className="error-state">
                Couldn&apos;t load recent activity: {recentEvents.error}
              </div>
            )}
            {recentEvents.data && recentEvents.data.length === 0 && (
              <div className="empty-state">No recent activity.</div>
            )}
            {recentEvents.data && recentEvents.data.length > 0 && (
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 12 }}>
                {recentEvents.data.map((ev) => (
                  <li key={ev.event_id} style={{ fontSize: 13 }}>
                    <div style={{ color: "var(--color-text-muted)", fontSize: 12 }}>
                      {new Date(ev.timestamp).toLocaleTimeString()} · {ev.source_feed}
                    </div>
                    <div>{ev.description}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

function StatsSkeleton() {
  return (
    <>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="card card-padded" style={{ flex: 1, minWidth: 150 }}>
          <div style={{ height: 12, width: "60%", background: "var(--color-border)", borderRadius: 3, marginBottom: 12 }} />
          <div style={{ height: 26, width: "40%", background: "var(--color-border)", borderRadius: 3 }} />
        </div>
      ))}
    </>
  );
}
