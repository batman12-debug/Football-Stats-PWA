import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { GoalPrediction } from "@/components/GoalPrediction";
import { PredictionBar } from "@/components/PredictionBar";
import { getPrediction } from "@/lib/api";
import { getConfidenceLevel, stripDisplayDashes } from "@/lib/utils";

interface MatchPredictionBlockProps {
  fixtureId: string;
  homeName: string;
  awayName: string;
}

export async function MatchPredictionBlock({
  fixtureId,
  homeName,
  awayName,
}: MatchPredictionBlockProps) {
  const prediction = await getPrediction(fixtureId);

  if (!prediction) {
    return (
      <div className="rounded-xl border border-card-border bg-card p-6 text-center text-sm text-muted">
        Prediction unavailable. The backend may be offline or data is not ready yet.
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-medium text-muted">
          {stripDisplayDashes(prediction.prediction_label)}
        </p>
        <ConfidenceBadge level={getConfidenceLevel(prediction.confidence_score)} />
      </div>

      <PredictionBar
        homeWin={prediction.home_win_probability}
        draw={prediction.draw_probability}
        awayWin={prediction.away_win_probability}
        homeName={homeName}
        awayName={awayName}
      />

      <GoalPrediction
        homeGoals={prediction.home_expected_goals}
        awayGoals={prediction.away_expected_goals}
        homeName={homeName}
        awayName={awayName}
      />
    </>
  );
}

export function MatchPredictionSkeleton() {
  return (
    <div className="space-y-4">
      <div className="skeleton h-10 w-full max-w-md rounded-lg" />
      <div className="skeleton h-24 w-full rounded-xl" />
      <div className="skeleton h-20 w-full rounded-xl" />
    </div>
  );
}
