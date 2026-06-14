import { readFileSync } from "node:fs";
import { join } from "node:path";

interface TournamentLogoProps {
  className?: string;
}

const TOURNAMENT_LOGO_SVG = readFileSync(
  join(process.cwd(), "public/wc2026-tournament-logo-display.svg"),
  "utf8",
);

/**
 * WC 2026 emblem for the home hero.
 * Inlined so embedded raster content renders (blocked when SVG is used as <img src>).
 */
export function TournamentLogo({
  className = "h-56 w-auto max-h-[22rem] max-w-[12rem] sm:h-64 lg:h-72 xl:h-80",
}: TournamentLogoProps) {
  return (
    <div
      className={`block shrink-0 [&>svg]:h-full [&>svg]:w-auto [&>svg]:max-h-full [&>svg]:max-w-full ${className}`}
      role="img"
      aria-label="FIFA World Cup 2026 official tournament emblem"
      dangerouslySetInnerHTML={{ __html: TOURNAMENT_LOGO_SVG }}
    />
  );
}
