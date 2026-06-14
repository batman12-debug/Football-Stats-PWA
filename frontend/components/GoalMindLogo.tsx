interface GoalMindLogoProps {
  className?: string;
  priority?: boolean;
}

/** GoalMind vector logo — transparent SVG (no white PNG box). */
export function GoalMindLogo({
  className = "h-9 w-auto max-h-20 max-w-[12rem]",
  priority = false,
}: GoalMindLogoProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/goalmind-logo.svg"
      alt="GoalMind"
      width={1536}
      height={1024}
      className={className}
      style={{ maxHeight: "5rem", maxWidth: "100%", width: "auto", height: "auto" }}
      decoding="async"
      fetchPriority={priority ? "high" : "auto"}
    />
  );
}
