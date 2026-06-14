interface MatchesBlobBackgroundProps {
  svg: string;
  variant?: "panel" | "tomorrow";
}

export function MatchesBlobBackground({
  svg,
  variant = "panel",
}: MatchesBlobBackgroundProps) {
  const className =
    variant === "tomorrow"
      ? "matches-blob matches-blob--tomorrow pointer-events-none"
      : "matches-blob matches-blob--panel pointer-events-none";

  return (
    <div
      className={className}
      data-visible="true"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
