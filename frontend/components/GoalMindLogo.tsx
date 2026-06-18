interface GoalMindLogoProps {
  className?: string;
  priority?: boolean;
}

/** CheckBoard logomark — vector SVG. */
export function GoalMindLogo({
  className = "h-9 w-auto max-h-20 max-w-[12rem]",
  priority = false,
}: GoalMindLogoProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/checkboard-logo.svg"
      alt="CheckBoard"
      width={1536}
      height={2752}
      className={className}
      style={{ maxHeight: "5rem", maxWidth: "100%", width: "auto", height: "auto" }}
      decoding="async"
      fetchPriority={priority ? "high" : "auto"}
    />
  );
}
