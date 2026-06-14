"use client";

import { useState } from "react";

import { MatchCard } from "@/components/MatchCard";
import { StandingsTable } from "@/components/StandingsTable";
import type { BracketFixture, MatchWithPrediction, TournamentBracket } from "@/types";

interface TournamentBracketViewProps {
  bracket: TournamentBracket;
}

function toMatchCardProps(fixture: BracketFixture): MatchWithPrediction {
  return { ...fixture, prediction: null };
}

export function TournamentBracketView({ bracket }: TournamentBracketViewProps) {
  const [openStage, setOpenStage] = useState<string>("group_stage");

  return (
    <div className="space-y-4">
      {bracket.stages.map((stage) => {
        const isOpen = openStage === stage.stage;
        const matchCount =
          (stage.groups?.reduce((n, g) => n + g.fixtures.length, 0) ?? 0) +
          stage.fixtures.length;

        return (
          <section
            key={stage.stage}
            className="overflow-hidden rounded-xl border border-card-border bg-card"
          >
            <button
              type="button"
              onClick={() => setOpenStage(isOpen ? "" : stage.stage)}
              className="flex w-full items-center justify-between px-4 py-4 text-left transition-colors hover:bg-card-border/30 sm:px-6"
            >
              <div>
                <h2 className="text-lg font-extrabold">{stage.label}</h2>
                <p className="text-xs text-muted">{matchCount} matches</p>
              </div>
              <span className="text-muted">{isOpen ? "▴" : "▾"}</span>
            </button>

            {isOpen && (
              <div className="border-t border-card-border px-4 pb-6 pt-4 sm:px-6">
                {stage.groups && stage.groups.length > 0 ? (
                  <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
                    {stage.groups.map((group) => (
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
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {stage.fixtures.map((fixture) => (
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
          </section>
        );
      })}
    </div>
  );
}
