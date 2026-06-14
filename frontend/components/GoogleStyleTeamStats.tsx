"use client";

import { FormBadgeStrip } from "@/components/FormBadgeStrip";
import { TeamFlagGlow } from "@/components/TeamFlagGlow";
import type { GroupStandingRow, TeamStats, TeamSummary } from "@/types";
import { formatPercent, stripDisplayDashes } from "@/lib/utils";

interface GoogleStyleTeamStatsProps {
  team: TeamSummary;
  stats: TeamStats;
  group: string | null;
  standing: GroupStandingRow | null;
}

interface StatChip {
  label: string;
  value: string;
}

function StatChipGrid({ chips }: { chips: StatChip[] }) {
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-card-border bg-card-border sm:grid-cols-4">
      {chips.map((chip) => (
        <div key={chip.label} className="bg-card px-4 py-3 text-center">
          <p className="text-lg font-bold tabular-nums sm:text-xl">{chip.value}</p>
          <p className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-muted">
            {chip.label}
          </p>
        </div>
      ))}
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-sm font-semibold tabular-nums">{value}</span>
    </div>
  );
}

export function GoogleStyleTeamStats({
  team,
  stats,
  group,
  standing,
}: GoogleStyleTeamStatsProps) {
  const historyChips: StatChip[] = [
    { label: "WC matches", value: String(stats.matches_played) },
    {
      label: "Goals / game",
      value: stats.avg_goals_scored.toFixed(1),
    },
    {
      label: "Conceded / game",
      value: stats.avg_goals_conceded.toFixed(1),
    },
    {
      label: "Form rating",
      value: formatPercent(stats.recent_form),
    },
  ];

  const tournamentChips: StatChip[] = standing
    ? [
        { label: "Played", value: String(standing.played) },
        { label: "Won", value: String(standing.won) },
        { label: "Drawn", value: String(standing.drawn) },
        { label: "Lost", value: String(standing.lost) },
        { label: "Goals", value: `${standing.goals_for}-${standing.goals_against}` },
        { label: "Points", value: String(standing.points) },
      ]
    : [];

  return (
    <article className="overflow-hidden rounded-2xl border border-card-border bg-card">
      {/* Header — Google knowledge panel style */}
      <header className="border-b border-card-border px-5 py-5 sm:px-6">
        <div className="flex items-start gap-4">
          <TeamFlagGlow team={team} size="lg" priority />
          <div className="min-w-0 flex-1">
            <h2 className="type-display text-2xl sm:text-3xl">{stripDisplayDashes(team.name)}</h2>
            <p className="mt-1 text-sm text-muted">
              FIFA World Cup 2026
              {group ? ` · ${group}` : ""}
            </p>
          </div>
        </div>
      </header>

      <div className="space-y-6 px-5 py-5 sm:px-6">
        {/* Recent form */}
        <section>
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted">
            Recent form
          </h3>
          <FormBadgeStrip form={stats.form_string} />
          <p className="mt-2 text-xs text-muted">
            Last World Cup matches (2018 &amp; 2022)
          </p>
        </section>

        {/* Tournament standing */}
        {standing && (
          <section>
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted">
              {group} standing
            </h3>
            <StatChipGrid chips={tournamentChips} />
          </section>
        )}

        {/* Historical performance */}
        <section>
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted">
            World Cup history
          </h3>
          <StatChipGrid chips={historyChips} />
        </section>

        {/* Detailed stats rows */}
        <section className="divide-y divide-card-border rounded-xl border border-card-border px-4">
          <StatRow
            label="Average possession"
            value={`${stats.possession_avg.toFixed(0)}%`}
          />
          <StatRow
            label="Goals scored per match"
            value={stats.avg_goals_scored.toFixed(2)}
          />
          <StatRow
            label="Goals conceded per match"
            value={stats.avg_goals_conceded.toFixed(2)}
          />
          <StatRow
            label="Matches in dataset"
            value={String(stats.matches_played)}
          />
          <StatRow label="Form rating" value={formatPercent(stats.recent_form)} />
        </section>
      </div>
    </article>
  );
}
