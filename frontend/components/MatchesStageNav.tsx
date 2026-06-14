"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import {
  TOMORROW_VIEW,
  TOURNAMENT_STAGES,
  formatDayLabel,
  getTomorrowPkt,
  matchesViewHref,
  parseMatchesView,
} from "@/lib/matches";

interface MatchesStageNavProps {
  className?: string;
}

export function MatchesStageNav({ className = "" }: MatchesStageNavProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentView = parseMatchesView(searchParams.get("view"));
  const isMatchesPage = pathname === "/matches";
  const tomorrowLabel = formatDayLabel(getTomorrowPkt());

  if (!isMatchesPage) return null;

  const linkClass = (active: boolean) =>
    `inline-flex shrink-0 items-center rounded-full px-4 py-2.5 text-sm font-medium transition-colors ${
      active
        ? "bg-win/15 text-win ring-1 ring-win/35"
        : "bg-card text-muted ring-1 ring-card-border active:bg-card-border/60"
    }`;

  return (
    <nav
      className={`matches-stage-nav ${className}`}
      aria-label="Tournament stages"
    >
      <div className="matches-stage-nav__track">
        <Link
          href={matchesViewHref(TOMORROW_VIEW)}
          className={linkClass(currentView === TOMORROW_VIEW)}
          aria-current={currentView === TOMORROW_VIEW ? "page" : undefined}
        >
          <span className="flex flex-col leading-tight">
            <span>Tomorrow</span>
            <span className="text-[11px] font-normal opacity-75">{tomorrowLabel}</span>
          </span>
        </Link>
        {TOURNAMENT_STAGES.map((stage) => (
          <Link
            key={stage.value}
            href={matchesViewHref(stage.value)}
            className={linkClass(currentView === stage.value)}
            aria-current={currentView === stage.value ? "page" : undefined}
          >
            {stage.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
