"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchLiveMatchStats } from "@/lib/api";
import { MatchScoreboard } from "@/components/MatchScoreboard";
import type { LiveMatchStats, LiveTeamStats } from "@/types";
import { hasScoreboard, isLiveStatus, formatMatchMinute, stripDisplayDashes } from "@/lib/utils";

interface LiveMatchStatsPanelProps {
  fixtureId: string;
  initialStatus: string;
  initialHomeGoals?: number | null;
  initialAwayGoals?: number | null;
}

interface StatRowConfig {
  key: keyof LiveTeamStats;
  label: string;
  format?: (value: number) => string;
  bar?: boolean;
}

const STAT_ROWS: StatRowConfig[] = [
  { key: "shots", label: "Shots" },
  { key: "shots_on_target", label: "Shots on target" },
  { key: "possession", label: "Possession", format: (v) => `${Math.round(v)}%`, bar: true },
  { key: "passes", label: "Passes" },
  { key: "pass_accuracy", label: "Pass accuracy", format: (v) => `${Math.round(v)}%` },
  { key: "fouls", label: "Fouls" },
  { key: "yellow_cards", label: "Yellow cards" },
  { key: "red_cards", label: "Red cards" },
  { key: "offsides", label: "Offsides" },
  { key: "corners", label: "Corners" },
];

const POLL_MS = 10_000;

function formatValue(value: number, row: StatRowConfig): string {
  if (row.format) return row.format(value);
  return String(value);
}

function ComparisonBar({
  homeValue,
  awayValue,
}: {
  homeValue: number;
  awayValue: number;
}) {
  const total = homeValue + awayValue || 1;
  const homePct = (homeValue / total) * 100;

  return (
    <div className="mt-2 flex h-1.5 overflow-hidden rounded-full bg-card-border">
      <div
        className="bg-win transition-all duration-500 ease-out motion-reduce:transition-none"
        style={{ width: `${homePct}%` }}
      />
      <div
        className="bg-loss transition-all duration-500 ease-out motion-reduce:transition-none"
        style={{ width: `${100 - homePct}%` }}
      />
    </div>
  );
}

export function LiveMatchStatsPanel({
  fixtureId,
  initialStatus,
  initialHomeGoals = null,
  initialAwayGoals = null,
}: LiveMatchStatsPanelProps) {
  const [stats, setStats] = useState<LiveMatchStats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const data = await fetchLiveMatchStats(fixtureId);
    setStats(data);
    setLoading(false);
  }, [fixtureId]);

  useEffect(() => {
    void load();
    const interval = setInterval(() => {
      void load();
    }, POLL_MS);
    return () => clearInterval(interval);
  }, [load]);

  const isLive =
    stats?.is_live ||
    initialStatus === "LIVE" ||
    ["1H", "2H", "HT", "ET", "P"].includes(initialStatus);

  const showScore =
    (stats && hasScoreboard(stats.home_goals, stats.away_goals)) ||
    hasScoreboard(initialHomeGoals, initialAwayGoals);

  if (loading && !stats) {
    if (isLive && showScore) {
      return (
        <section className="overflow-hidden rounded-xl border border-loss/40 bg-card ring-1 ring-loss/20">
          <header className="flex items-center justify-between border-b border-card-border px-5 py-4 sm:px-6">
            <div>
              <h2 className="text-sm font-medium uppercase tracking-wide text-muted">
                Team stats
              </h2>
              <p className="mt-1 text-xs text-muted">Loading live stats…</p>
            </div>
            <span className="flex items-center gap-2 rounded-full bg-loss/15 px-3 py-1 text-xs font-bold uppercase text-loss ring-1 ring-loss/30">
              <span className="h-2 w-2 animate-pulse rounded-full bg-loss" aria-hidden="true" />
              Live
            </span>
          </header>
          <div className="px-5 py-6 sm:px-6">
            <div className="flex items-center justify-center">
              <MatchScoreboard
                homeGoals={initialHomeGoals}
                awayGoals={initialAwayGoals}
                status={initialStatus}
                size="lg"
              />
            </div>
          </div>
          <div className="border-t border-card-border px-5 py-4 sm:px-6">
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="skeleton h-8 w-full rounded" />
              ))}
            </div>
          </div>
        </section>
      );
    }

    return (
      <section className="rounded-xl border border-card-border bg-card p-6">
        <div className="skeleton mb-4 h-6 w-32 rounded" />
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-10 w-full rounded" />
          ))}
        </div>
      </section>
    );
  }

  if (!stats || !isLive) {
    return null;
  }

  return (
    <section className="overflow-hidden rounded-xl border border-card-border bg-card">
      <header className="flex items-center justify-between border-b border-card-border px-5 py-4 sm:px-6">
        <div>
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted">
            Team stats
          </h2>
          <p className="mt-1 text-xs text-muted">
            Updates every {POLL_MS / 1000}s · {formatMatchMinute(stats.minute, stats.status) ?? `${stats.minute}'`} played
          </p>
        </div>
        <span className="flex items-center gap-2 rounded-full bg-loss/15 px-3 py-1 text-xs font-bold uppercase text-loss ring-1 ring-loss/30">
          <span className="h-2 w-2 animate-pulse rounded-full bg-loss" aria-hidden="true" />
          Live
        </span>
      </header>

      {showScore ? (
        <div className="border-b border-card-border px-5 py-6 sm:px-6">
          <div className="flex items-center justify-center gap-6 sm:gap-10">
            <p className="max-w-[8rem] truncate text-center text-base font-bold sm:max-w-none">
              {stripDisplayDashes(stats.home_team)}
            </p>
            <MatchScoreboard
              homeGoals={stats.home_goals}
              awayGoals={stats.away_goals}
              status={stats.status}
              size="lg"
              liveMinute={stats.minute}
            />
            <p className="max-w-[8rem] truncate text-center text-base font-bold sm:max-w-none">
              {stripDisplayDashes(stats.away_team)}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-[1fr_auto_1fr] gap-3 border-b border-card-border px-5 py-4 text-center text-sm font-semibold sm:px-6">
        <span className="truncate text-left">{stripDisplayDashes(stats.home_team)}</span>
        <span className="text-xs font-medium uppercase tracking-wide text-muted">vs</span>
        <span className="truncate text-right">{stripDisplayDashes(stats.away_team)}</span>
      </div>

      <div className="divide-y divide-card-border px-5 sm:px-6">
        {STAT_ROWS.map((row) => {
          const homeValue = stats.home[row.key];
          const awayValue = stats.away[row.key];

          return (
            <div key={row.key} className="py-4">
              <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                <span className="text-left text-lg font-bold tabular-nums">
                  {formatValue(homeValue, row)}
                </span>
                <span className="min-w-[7rem] text-center text-xs font-medium text-muted">
                  {row.label}
                </span>
                <span className="text-right text-lg font-bold tabular-nums">
                  {formatValue(awayValue, row)}
                </span>
              </div>
              {row.bar && (
                <ComparisonBar homeValue={homeValue} awayValue={awayValue} />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
