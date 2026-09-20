"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ApiError,
  listExams,
  registerExam,
  triggerSyntheticFeed,
} from "@/lib/api";
import type { ExamSummary } from "@/lib/types";

export default function ExaminationsPage() {
  const [exams, setExams] = useState<ExamSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    listExams()
      .then((data) => {
        setExams(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof ApiError ? err.message : "Unexpected error loading examinations."
        );
        setLoading(false);
      });
  }

  useEffect(load, []);

  async function handleRun(examId: string) {
    setRunningId(examId);
    setRunError(null);
    try {
      await triggerSyntheticFeed(examId, 10);
      load();
    } catch (err) {
      setRunError(
        err instanceof ApiError ? err.message : "Failed to run synthetic feed."
      );
    } finally {
      setRunningId(null);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <h1 style={{ fontSize: 24 }}>Examinations</h1>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "Register exam"}
        </button>
      </div>

      {showForm && (
        <RegisterExamForm
          onRegistered={() => {
            setShowForm(false);
            load();
          }}
        />
      )}

      {runError && (
        <div className="error-state" style={{ marginBottom: 16 }}>
          {runError}
        </div>
      )}

      <div className="card">
        {loading && (
          <div style={{ padding: 20, color: "var(--color-text-muted)" }}>
            Loading examinations…
          </div>
        )}
        {error && (
          <div className="error-state" style={{ margin: 16 }}>
            Couldn&apos;t load examinations: {error}
          </div>
        )}
        {exams && exams.length === 0 && (
          <div className="empty-state">
            No examinations registered yet. Register one to start monitoring.
          </div>
        )}
        {exams && exams.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Scheduled</th>
                <th>Questions</th>
                <th>Events today</th>
                <th>Open reviews</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {exams.map((e) => (
                <tr key={e.exam_id}>
                  <td>{e.title}</td>
                  <td>{new Date(e.scheduled_start).toLocaleString()}</td>
                  <td>{e.question_count}</td>
                  <td>{e.events_today}</td>
                  <td>
                    {e.open_reviews > 0 ? (
                      <Link href="/investigations">{e.open_reviews}</Link>
                    ) : (
                      "0"
                    )}
                  </td>
                  <td>{e.monitoring_status}</td>
                  <td>
                    <button
                      className="btn-secondary"
                      style={{ padding: "5px 10px", fontSize: 12 }}
                      disabled={runningId === e.exam_id}
                      onClick={() => handleRun(e.exam_id)}
                    >
                      {runningId === e.exam_id ? "Running…" : "Run synthetic feed"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}

function RegisterExamForm({ onRegistered }: { onRegistered: () => void }) {
  const [title, setTitle] = useState("");
  const [scheduledStart, setScheduledStart] = useState("");
  const [questionsText, setQuestionsText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const lines = questionsText
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (!title.trim() || !scheduledStart || lines.length === 0) {
      setError("Title, scheduled start, and at least one reference question are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await registerExam({
        title: title.trim(),
        scheduled_start: new Date(scheduledStart).toISOString(),
        reference_questions: lines.map((text, i) => ({
          question_id: `q${i + 1}`,
          text,
        })),
      });
      onRegistered();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to register exam."
      );
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="card card-padded"
      style={{ marginBottom: 20, display: "flex", flexDirection: "column", gap: 14 }}
    >
      {error && <div className="error-state">{error}</div>}
      <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
        Title
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="CS301 Midterm"
          style={{
            padding: "8px 10px",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            fontSize: 13,
          }}
        />
      </label>
      <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
        Scheduled start
        <input
          type="datetime-local"
          value={scheduledStart}
          onChange={(e) => setScheduledStart(e.target.value)}
          style={{
            padding: "8px 10px",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            fontSize: 13,
          }}
        />
      </label>
      <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
        Reference questions (one per line)
        <textarea
          value={questionsText}
          onChange={(e) => setQuestionsText(e.target.value)}
          rows={5}
          placeholder={"Explain the difference between TCP and UDP...\nDescribe how a hash table resolves collisions..."}
          style={{
            padding: "8px 10px",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            fontSize: 13,
            fontFamily: "var(--font-sans)",
            resize: "vertical",
          }}
        />
      </label>
      <div>
        <button className="btn-primary" type="submit" disabled={submitting}>
          {submitting ? "Registering…" : "Register exam"}
        </button>
      </div>
    </form>
  );
}
