export function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="card card-padded" style={{ flex: 1, minWidth: 150 }}>
      <div
        style={{
          fontSize: 12,
          color: "var(--color-text-muted)",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div style={{ fontFamily: "var(--font-serif)", fontSize: 30 }}>
        {value}
      </div>
    </div>
  );
}
