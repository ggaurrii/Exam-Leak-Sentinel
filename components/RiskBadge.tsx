import type { RiskTier } from "@/lib/types";

const TIER_STYLES: Record<RiskTier, { fg: string; bg: string }> = {
  Low: { fg: "var(--color-risk-low)", bg: "var(--color-risk-low-bg)" },
  Medium: { fg: "var(--color-risk-medium)", bg: "var(--color-risk-medium-bg)" },
  High: { fg: "var(--color-risk-high)", bg: "var(--color-risk-high-bg)" },
};

export function RiskBadge({
  tier,
  score,
}: {
  tier: RiskTier;
  score?: number;
}) {
  const style = TIER_STYLES[tier];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        color: style.fg,
        background: style.bg,
        borderRadius: 4,
        padding: "3px 9px",
        fontSize: 12,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      {tier}
      {typeof score === "number" && (
        <span style={{ fontWeight: 400, opacity: 0.85 }}>
          {score.toFixed(2)}
        </span>
      )}
    </span>
  );
}
