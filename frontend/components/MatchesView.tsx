"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { MatchCard } from "@/components/MatchCard";
import { MatchesBlobBackground } from "@/components/MatchesBlobBackground";
import { MatchesStageNav } from "@/components/MatchesStageNav";
import { StandingsTable } from "@/components/StandingsTable";
import { fetchTournamentBracketClient } from "@/lib/api";
import {
  TOMORROW_VIEW,
  collectAllFixtures,
  collectStageFixtures,
  filterFixturesForTomorrow,
  findStage,
  formatDayLabel,
  getTomorrowPkt,
  parseMatchesView,
} from "@/lib/matches";
import { isLiveStatus } from "@/lib/utils";
import type { BracketFixture, MatchWithPrediction, TournamentBracket } from "@/types";

const BRACKET_POLL_MS = 30_000;

interface MatchesViewProps {
  bracket: TournamentBracket;
  tomorrowBlobSvg?: string;
  stageBlobSvg?: string;
}

function toMatchCardProps(fixture: BracketFixture): MatchWithPrediction {
  return { ...fixture, prediction: null };
}

function bracketHasLiveMatches(bracket: TournamentBracket): boolean {
  return collectAllFixtures(bracket).some((fixture) => isLiveStatus(fixture.status));
}

export function MatchesView({
  bracket: initialBracket,
  tomorrowBlobSvg,
  stageBlobSvg,
}: MatchesViewProps) {
  const searchParams = useSearchParams();
  const [bracket, setBracket] = useState(initialBracket);
  const tomorrow = useMemo(() => getTomorrowPkt(), []);
  const tomorrowLabel = formatDayLabel(tomorrow);
  const selectedView = parseMatchesView(searchParams.get("view"));

  const tomorrowFixtures = useMemo(
    () => filterFixturesForTomorrow(collectAllFixtures(bracket), tomorrow),
    [bracket, tomorrow]
  );

  const activeStage = selectedView === TOMORROW_VIEW ? null : findStage(bracket, selectedView);
  const isTomorrow = selectedView === TOMORROW_VIEW;
  const matchCount = isTomorrow
    ? tomorrowFixtures.length
    : activeStage
      ? collectStageFixtures(activeStage).length
      : 0;

  const refreshBracket = useCallback(async () => {
    const data = await fetchTournamentBracketClient();
    if (data) setBracket(data);
  }, []);

  useEffect(() => {
    setBracket(initialBracket);
  }, [initialBracket]);

  useEffect(() => {
    if (!bracketHasLiveMatches(bracket)) return;

    const interval = setInterval(() => {
      void refreshBracket();
    }, BRACKET_POLL_MS);

    return () => clearInterval(interval);
  }, [bracket, refreshBracket]);

  const pageHeader = (
    <div>
      <h1 className="type-display text-3xl sm:text-4xl">Matches</h1>
      <p className="mt-2 text-sm text-muted sm:text-base">
        Tomorrow&apos;s fixtures by default. Pick a stage below or from the Matches menu.
      </p>
    </div>
  );

  const viewContent = (
    <section className="space-y-6">
      <MatchesStageNav className="sm:hidden" />

      <div>
        <h2 className="type-title text-xl">
          {isTomorrow ? "Tomorrow" : activeStage?.label ?? "Matches"}
        </h2>
        <p className="mt-1 text-sm text-muted">
          {isTomorrow
            ? `${tomorrowLabel} (PKT). Swipe stages above or use the Matches menu.`
            : activeStage
              ? `All ${activeStage.label.toLowerCase()} fixtures`
              : "Select a stage from the Matches menu"}
        </p>
      </div>

      <p className="text-xs text-muted">
        {matchCount} {matchCount === 1 ? "match" : "matches"}
      </p>

      {isTomorrow && (
        <>
          {tomorrowFixtures.length === 0 ? (
            <div className="rounded-xl border border-card-border bg-black/70 p-8 text-center backdrop-blur-[3px]">
              <p className="font-semibold">No matches tomorrow</p>
              <p className="mt-2 text-sm text-muted">
                Use the Matches menu to browse the full tournament schedule.
              </p>
            </div>
          ) : (
            <div className="match-card-grid">
              {tomorrowFixtures.map((fixture) => (
                <MatchCard key={fixture.id} match={toMatchCardProps(fixture)} />
              ))}
            </div>
          )}
        </>
      )}

      {!isTomorrow && activeStage && (
        <div className="rounded-xl border border-card-border bg-black/70 p-4 backdrop-blur-[3px] sm:p-6">
          {activeStage.groups && activeStage.groups.length > 0 ? (
            <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
              {activeStage.groups.map((group) => (
                <div key={group.group} className="space-y-3">
                  <h3 className="text-sm font-bold text-win">{group.group}</h3>
                  <StandingsTable standings={group.standings} />
                  <div className="grid gap-3">
                    {group.fixtures.map((fixture) => (
                      <MatchCard
                        key={fixture.id}
                        match={toMatchCardProps(fixture)}
                        compact
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="match-card-grid">
              {activeStage.fixtures.map((fixture) => (
                <MatchCard
                  key={fixture.id}
                  match={toMatchCardProps(fixture)}
                  showMatchNumber
                />
              ))}
            </div>
          )}
        </div>
      )}

      {!isTomorrow && !activeStage && (
        <div className="rounded-xl border border-card-border bg-black/70 p-8 text-center backdrop-blur-[3px]">
          <p className="font-semibold">Stage not found</p>
          <p className="mt-2 text-sm text-muted">
            Choose a stage from the Matches menu in the nav.
          </p>
        </div>
      )}
    </section>
  );

  if (isTomorrow && tomorrowBlobSvg) {
    return (
      <div className="matches-tomorrow-scene relative isolate pt-8 sm:pt-10">
        <MatchesBlobBackground svg={tomorrowBlobSvg} variant="tomorrow" />
        <div className="relative z-10 space-y-8 pb-2">
          {pageHeader}
          {viewContent}
        </div>
      </div>
    );
  }

  return (
    <div className="matches-panel relative isolate pt-8 sm:pt-10">
      {stageBlobSvg ? <MatchesBlobBackground svg={stageBlobSvg} variant="panel" /> : null}
      <div className="relative z-10 space-y-8">
        {pageHeader}
        {viewContent}
      </div>
    </div>
  );
}
