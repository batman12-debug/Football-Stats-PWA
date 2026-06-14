import type { GoalScorer } from "@/types";
import { stripDisplayDashes } from "@/lib/utils";

interface MatchGoalScorersProps {
  scorers: GoalScorer[];
  homeTeam: string;
  awayTeam: string;
}

export function MatchGoalScorers({
  scorers,
  homeTeam,
  awayTeam,
}: MatchGoalScorersProps) {
  if (scorers.length === 0) {
    return null;
  }

  const home = scorers.filter((g) => g.team === homeTeam);
  const away = scorers.filter((g) => g.team === awayTeam);

  return (
    <section className="rounded-xl border border-card-border bg-card p-5 sm:p-6">
      <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted">
        Goal scorers
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <GoalList team={homeTeam} goals={home} />
        <GoalList team={awayTeam} goals={away} />
      </div>
    </section>
  );
}

function GoalList({ team, goals }: { team: string; goals: GoalScorer[] }) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold">{stripDisplayDashes(team)}</p>
      {goals.length === 0 ? (
        <p className="text-sm text-muted">None</p>
      ) : (
        <ul className="space-y-1.5">
          {goals.map((goal) => (
            <li key={`${goal.player_name}-${goal.minute}`} className="text-sm">
              <span className="font-medium">{stripDisplayDashes(goal.player_name)}</span>
              {goal.is_own_goal ? (
                <span className="text-muted"> (OG)</span>
              ) : null}
              <span className="text-muted"> · {goal.minute}&apos;</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
