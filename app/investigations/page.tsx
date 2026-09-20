"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, listInvestigations } from "@/lib/api";
import type { Investigation, ReviewStatus } from "@/lib/types";

const FILTERS: { label: string; value: ReviewStatus | undefined }[] = [
  { label: "All", value: undefined },
  { label: "Pending", value: "Pending" },
  { label: "Reviewed", value: "Reviewed" },
];

export default function InvestigationsPage() {
  const [filter, setFilter] = useState<ReviewStatus | undefined>("Pending");
  const [investigations, setInvestigations] = useState<Investigation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listInvestigations(filter)
      .then((res) => {
        if (!cancelled) {
          setInvestigations(res.investigations);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "Unexpected error loading investigations."
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
        <h1 style={{ fontSize: 24 }}>Investigations</h1>
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
            Loading investigations…
          </div>
        )}
        {error && (
          <div className="error-state" style={{ margin: 16 }}>
            Couldn&apos;t load investigations: {error}
          </div>
        )}
        {investigations && investigations.length === 0 && (
          <div className="empty-state">
            No {filter ? filter.toLowerCase() : ""} investigations right now.
          </div>
        )}
        {investigations && investigations.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Investigation</th>
                <th>Alert</th>
                <th>Status</th>
                <th>Opened</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {investigations.map((inv) => (
                <tr key={inv.investigation_id}>
                  <td style={{ fontFamily: "monospace", fontSize: 12 }}>
                    {inv.investigation_id.slice(0, 8)}
                  </td>
                  <td>
                    <Link href={`/alerts/${inv.alert_id}`}>
                      {inv.alert_id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>{inv.status}</td>
                  <td>{new Date(inv.created_at).toLocaleString()}</td>
                  <td>{new Date(inv.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
