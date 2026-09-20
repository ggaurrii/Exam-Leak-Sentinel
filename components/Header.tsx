"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { listExams } from "@/lib/api";
import type { ExamSummary } from "@/lib/types";

const TABS: { label: string; href: string }[] = [
  { label: "Overview", href: "/overview" },
  { label: "Examinations", href: "/examinations" },
  { label: "Monitoring", href: "/monitoring" },
  { label: "Alerts", href: "/alerts" },
  { label: "Investigations", href: "/investigations" },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header
      style={{
        background: "var(--color-header-bg)",
        color: "var(--color-header-text)",
        height: "var(--header-height)",
        display: "flex",
        alignItems: "center",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <div
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          width: "100%",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 36 }}>
          <span
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 17,
              letterSpacing: "0.01em",
            }}
          >
            Exam Leak Sentinel
          </span>
          <nav style={{ display: "flex", gap: 4 }}>
            {TABS.map((tab) => {
              const active =
                pathname === tab.href || pathname?.startsWith(tab.href + "/");
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  style={{
                    color: active ? "#ffffff" : "rgba(231,233,242,0.65)",
                    fontSize: 13,
                    fontWeight: active ? 600 : 400,
                    padding: "8px 12px",
                    borderRadius: 4,
                    background: active ? "rgba(255,255,255,0.08)" : "transparent",
                  }}
                >
                  {tab.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <MonitoringIndicator />
      </div>
    </header>
  );
}

function MonitoringIndicator() {
  const [exams, setExams] = useState<ExamSummary[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listExams()
      .then((data) => {
        if (!cancelled) setExams(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  let color = "#697082";
  let label = "Checking backend…";

  if (failed) {
    color = "var(--color-risk-high)";
    label = "Backend unreachable";
  } else if (exams) {
    const active = exams.filter((e) => e.monitoring_status === "Active");
    if (active.length > 0) {
      color = "var(--color-risk-low)";
      label = `Monitoring live · ${active.length} exam${active.length === 1 ? "" : "s"}`;
    } else {
      color = "#697082";
      label = "No active monitoring";
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 7,
        fontSize: 12,
        color: "rgba(231,233,242,0.75)",
      }}
      title={label}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {label}
    </div>
  );
}
