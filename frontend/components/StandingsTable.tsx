import type { GroupStandingRow } from "@/types";
import { stripDisplayDashes } from "@/lib/utils";

interface StandingsTableProps {
  standings: GroupStandingRow[];
}

export function StandingsTable({ standings }: StandingsTableProps) {
  if (standings.length === 0) {
    return (
      <p className="text-xs text-muted">Standings update as results come in.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[280px] text-xs">
        <thead>
          <tr className="border-b border-card-border text-left text-muted">
            <th className="pb-2 pr-2">Team</th>
            <th className="pb-2 px-1 text-center">P</th>
            <th className="pb-2 px-1 text-center">W</th>
            <th className="pb-2 px-1 text-center">D</th>
            <th className="pb-2 px-1 text-center">L</th>
            <th className="pb-2 px-1 text-center">GD</th>
            <th className="pb-2 pl-1 text-center">Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row, index) => (
            <tr
              key={row.team}
              className={`border-b border-card-border/50 ${
                index < 2 ? "text-win" : index === 2 ? "text-draw" : ""
              }`}
            >
              <td className="py-1.5 pr-2 font-medium">{stripDisplayDashes(row.team)}</td>
              <td className="px-1 text-center">{row.played}</td>
              <td className="px-1 text-center">{row.won}</td>
              <td className="px-1 text-center">{row.drawn}</td>
              <td className="px-1 text-center">{row.lost}</td>
              <td className="px-1 text-center">
                {row.goal_diff > 0 ? `+${row.goal_diff}` : row.goal_diff}
              </td>
              <td className="pl-1 text-center font-bold">{row.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
