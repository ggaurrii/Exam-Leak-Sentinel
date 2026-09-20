"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, listAlerts } from "@/lib/api";
import type { AlertSummary, RiskTier } from "@/lib/types";
import { RiskBadge } from "@/components/RiskBadge";

const FILTERS: { label: string; value: RiskTier | undefined }[] = [
  { label: "All", value: undefined },
  { label: "High", value: "High" },
  { label: "Medium", value: "Medium" },
  { label: "Low", value: "Low" },
];

export default function AlertsPage() {
  const [filter, setFilter] = useState<RiskTier | undefined>(undefined);
  const [alerts, setAlerts] = useState<AlertSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listAlerts(filter)
      .then((res) => {
        if (!cancelled) {
          setAlerts(res.alerts);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "Unexpected error loading alerts."
        );
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <main className="page">
      <div className="page-header">
        <h1 style={{ fontSize: 24 }}>Alerts</h1>
        <div style={{ display: "flex", gap: 4 }}>
          {FILTERS.map((f) => (
            <button
              key={f.label}
              onClick={() => setFilter(f.value)}
              className={filter === f.value ? "btn-primary" : "btn-secondary"}
              style={{ padding: "7px 14px" }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        {loading && (
          <div style={{ padding: 20, color: "var(--color-text-muted)" }}>
            Loading alerts…
          </div>
        )}
        {error && (
          <div className="error-state" style={{ margin: 16 }}>
            Couldn&apos;t load alerts: {error}
          </div>
        )}
        {alerts && alerts.length === 0 && (
          <div className="empty-state">
            No alerts{filter ? ` at ${filter} risk` : ""} yet. Register an exam
            and run the synthetic feed from the Overview page to generate some.
          </div>
        )}
        {alerts && alerts.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Alert</th>
                <th>Source</th>
                <th>Risk</th>
                <th>Review status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.alert_id}>
                  <td>
                    <Link href={`/alerts/${a.alert_id}`}>
                      {a.alert_id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>{a.source_feed}</td>
                  <td>
                    <RiskBadge tier={a.risk_tier} score={a.similarity_score} />
                  </td>
                  <td>{a.review_status}</td>
                  <td>{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
