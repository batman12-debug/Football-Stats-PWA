import type { TeamStats } from "@/types";
import { formToDisplay, formatPercent, stripDisplayDashes } from "@/lib/utils";

interface TeamStatsPanelProps {
  homeStats: TeamStats;
  awayStats: TeamStats;
}

interface StatRow {
  label: string;
  home: string;
  away: string;
}

function buildRows(homeStats: TeamStats, awayStats: TeamStats): StatRow[] {
  return [
    {
      label: "Form (last 5)",
      home: formToDisplay(homeStats.form_string, homeStats.recent_form),
      away: formToDisplay(awayStats.form_string, awayStats.recent_form),
    },
    {
      label: "Goals scored (avg)",
      home: homeStats.avg_goals_scored.toFixed(1),
      away: awayStats.avg_goals_scored.toFixed(1),
    },
    {
      label: "Goals conceded (avg)",
      home: homeStats.avg_goals_conceded.toFixed(1),
      away: awayStats.avg_goals_conceded.toFixed(1),
    },
    {
      label: "Possession (avg)",
      home: `${homeStats.possession_avg.toFixed(0)}%`,
      away: `${awayStats.possession_avg.toFixed(0)}%`,
    },
    {
      label: "Form rating",
      home: formatPercent(homeStats.recent_form),
      away: formatPercent(awayStats.recent_form),
    },
  ];
}

export function TeamStatsPanel({ homeStats, awayStats }: TeamStatsPanelProps) {
  const rows = buildRows(homeStats, awayStats);

  return (
    <section className="rounded-xl border border-card-border bg-card p-5 sm:p-6">
      <h2 className="mb-4 text-sm font-medium text-muted">Team Statistics</h2>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[320px] text-sm">
          <thead>
            <tr className="border-b border-card-border text-left">
              <th className="pb-3 pr-4 font-medium text-muted">Stat</th>
              <th className="pb-3 pr-4 font-semibold">{stripDisplayDashes(homeStats.name)}</th>
              <th className="pb-3 font-semibold">{stripDisplayDashes(awayStats.name)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-card-border/60">
                <td className="py-3 pr-4 text-muted">{row.label}</td>
                <td className="py-3 pr-4 font-medium">{row.home}</td>
                <td className="py-3 font-medium">{row.away}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
