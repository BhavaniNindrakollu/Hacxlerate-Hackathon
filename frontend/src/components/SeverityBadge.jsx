const styles = {
  High: "bg-red-500/15 text-red-400 border border-red-500/30",
  Medium: "bg-amber-500/15 text-amber-400 border border-amber-500/30",
  Low: "bg-yellow-500/15 text-yellow-300 border border-yellow-500/30",
  Safe: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
  Official: "bg-sky-500/15 text-sky-400 border border-sky-500/30",
};

export default function SeverityBadge({ verdict = "Safe", className = "" }) {
  const badgeStyle = styles[verdict] || styles.Safe;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide ${badgeStyle} ${className}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          verdict === "High"
            ? "bg-red-400 animate-pulse"
            : verdict === "Medium"
            ? "bg-amber-400"
            : verdict === "Low"
            ? "bg-yellow-300"
            : verdict === "Official"
            ? "bg-sky-400"
            : "bg-emerald-400"
        }`}
      />
      {verdict.toUpperCase()}
    </span>
  );
}
