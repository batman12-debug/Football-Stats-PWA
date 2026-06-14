import Link from "next/link";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { LiveMatchStatsPanel } from "@/components/LiveMatchStatsPanel";
import { MatchGoalScorers } from "@/components/MatchGoalScorers";
import { MatchHeader } from "@/components/MatchHeader";
import {
  MatchPredictionBlock,
  MatchPredictionSkeleton,
} from "@/components/MatchPredictionBlock";
import { TeamStatsPanel } from "@/components/TeamStatsPanel";
import { getMatchDetail } from "@/lib/api";
import { isValidFixtureId } from "@/lib/security";
import { isLiveStatus, stripDisplayDashes } from "@/lib/utils";

interface MatchDetailPageProps {
  params: { id: string };
}

export default async function MatchDetailPage({ params }: MatchDetailPageProps) {
  if (!isValidFixtureId(params.id)) {
    notFound();
  }

  const match = await getMatchDetail(params.id);

  if (!match) {
    notFound();
  }

  const isLive = isLiveStatus(match.status);

  return (
    <main className="container mx-auto bg-black px-4 py-8 sm:py-10">
      <Link
        href="/matches"
        className="mb-6 inline-flex min-h-11 items-center py-2 text-sm text-muted transition-colors hover:text-white"
      >
        ← Back to matches
      </Link>

      <div className="space-y-6">
        <h1 className="sr-only">
          {stripDisplayDashes(match.home_team.name)} vs {stripDisplayDashes(match.away_team.name)}
        </h1>
        <MatchHeader
          homeTeam={match.home_team}
          awayTeam={match.away_team}
          date={match.date}
          venue={match.venue}
          status={match.status}
          homeGoals={match.home_goals}
          awayGoals={match.away_goals}
        />

        <LiveMatchStatsPanel
          fixtureId={params.id}
          initialStatus={match.status}
          initialHomeGoals={match.home_goals}
          initialAwayGoals={match.away_goals}
        />

        {match.goal_scorers && match.goal_scorers.length > 0 ? (
          <MatchGoalScorers
            scorers={match.goal_scorers}
            homeTeam={match.home_team.name}
            awayTeam={match.away_team.name}
          />
        ) : null}

        {isLive ? null : (
          <Suspense fallback={<MatchPredictionSkeleton />}>
            <MatchPredictionBlock
              fixtureId={params.id}
              homeName={match.home_team.name}
              awayName={match.away_team.name}
            />
          </Suspense>
        )}

        {!isLive ? (
          <TeamStatsPanel homeStats={match.home_stats} awayStats={match.away_stats} />
        ) : null}
      </div>
    </main>
  );
}
