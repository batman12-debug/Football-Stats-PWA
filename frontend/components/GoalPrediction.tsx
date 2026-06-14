import { formatGoals, stripDisplayDashes } from "@/lib/utils";

interface GoalPredictionProps {
  homeGoals: number;
  awayGoals: number;
  homeName: string;
  awayName: string;
}

export function GoalPrediction({
  homeGoals,
  awayGoals,
  homeName,
  awayName,
}: GoalPredictionProps) {
  return (
    <div className="rounded-xl border border-card-border bg-card p-5 sm:p-6">
      <p className="mb-2 text-sm font-medium text-muted">Expected Goals</p>
      <p className="type-display text-4xl sm:text-5xl">
        <span className="text-win">{formatGoals(homeGoals)}</span>
        <span className="mx-3 text-muted">-</span>
        <span className="text-loss">{formatGoals(awayGoals)}</span>
      </p>
      <p className="mt-4 max-w-prose type-copy text-sm text-muted">
        Based on each team&apos;s average goals scored, adjusted for possession.
        {homeGoals > awayGoals
          ? ` ${stripDisplayDashes(homeName)} is projected to create more scoring chances.`
          : homeGoals < awayGoals
            ? ` ${stripDisplayDashes(awayName)} is projected to create more scoring chances.`
            : " Both teams are projected to score at a similar rate."}
      </p>
    </div>
  );
}
