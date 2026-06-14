interface FormBadgeStripProps {
  form: string | null;
  className?: string;
}

function badgeClass(result: string): string {
  switch (result.toUpperCase()) {
    case "W":
      return "bg-win/15 text-win ring-1 ring-win/30";
    case "D":
      return "bg-draw/15 text-draw ring-1 ring-draw/30";
    case "L":
      return "bg-loss/15 text-loss ring-1 ring-loss/30";
    default:
      return "bg-card-border text-muted";
  }
}

export function FormBadgeStrip({ form, className = "" }: FormBadgeStripProps) {
  const results = (form ?? "").slice(-5).toUpperCase().split("").filter(Boolean);

  if (results.length === 0) {
    return (
      <p className={`text-xs text-muted ${className}`}>No recent World Cup form data</p>
    );
  }

  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`}>
      {results.map((result, index) => (
        <span
          key={`${result}-${index}`}
          className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${badgeClass(result)}`}
          title={result === "W" ? "Win" : result === "D" ? "Draw" : "Loss"}
        >
          {result}
        </span>
      ))}
    </div>
  );
}
