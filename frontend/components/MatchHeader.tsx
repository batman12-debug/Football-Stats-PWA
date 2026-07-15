import Image from "next/image";

import { MatchScoreboard } from "@/components/MatchScoreboard";
import { TeamFlagGlow } from "@/components/TeamFlagGlow";
import { PinButton } from "@/components/pin/PinButton";
import { isQatarTeam } from "@/lib/isQatarTeam";
import type { TeamSummary } from "@/types";
import { formatMatchDate, isLiveStatus, stripDisplayDashes } from "@/lib/utils";

interface MatchHeaderProps {
  fixtureId: string;
  homeTeam: TeamSummary;
  awayTeam: TeamSummary;
  date: string;
  venue: string | null;
  status: string;
  homeGoals?: number | null;
  awayGoals?: number | null;
}

function LargeTeamFlag({ team }: { team: TeamSummary }) {
  if (isQatarTeam(team)) {
    return <TeamFlagGlow team={team} size="lg" priority />;
  }

  return (
    <div className="relative flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-card-border bg-card-border sm:h-20 sm:w-20 md:h-24 md:w-24">
      {team.logo ? (
        <Image
          src={team.logo}
          alt=""
          width={96}
          height={96}
          className="h-full w-full object-cover"
          priority
        />
      ) : (
        <span className="text-lg font-extrabold text-muted">
          {team.code ?? team.name.slice(0, 3).toUpperCase()}
        </span>
      )}
    </div>
  );
}

export function MatchHeader({
  fixtureId,
  homeTeam,
  awayTeam,
  date,
  venue,
  status,
  homeGoals = null,
  awayGoals = null,
}: MatchHeaderProps) {
  const isLive = isLiveStatus(status);

  return (
    <header
      className={`relative rounded-xl border bg-card p-4 sm:p-6 md:p-8 ${
        isLive ? "border-loss/40 ring-1 ring-loss/20" : "border-card-border"
      }`}
    >
      <PinButton
        fixtureId={fixtureId}
        homeName={homeTeam.name}
        awayName={awayTeam.name}
        homeCode={homeTeam.code}
        awayCode={awayTeam.code}
        homeLogo={homeTeam.logo}
        awayLogo={awayTeam.logo}
        stageLabel={null}
        kickoffIso={date}
        className="absolute right-3 top-3 sm:right-4 sm:top-4"
      />

      <div className="type-caps mb-4 flex flex-wrap items-center justify-center gap-2 text-center text-xs text-muted">
        <span>{formatMatchDate(date)}</span>
        <span aria-hidden="true">·</span>
        {isLive ? (
          <span className="flex items-center gap-1.5 rounded-full bg-loss/15 px-2 py-0.5 font-bold text-loss ring-1 ring-loss/30">
            <span className="h-2 w-2 animate-pulse rounded-full bg-loss" aria-hidden="true" />
            LIVE
          </span>
        ) : (
          <span>{status}</span>
        )}
      </div>

      <div className="match-card-teams gap-3 sm:gap-4">
        <div className="match-card-teams__row gap-x-3 sm:gap-x-6 md:gap-x-10">
          <div className="flex justify-center">
            <LargeTeamFlag team={homeTeam} />
          </div>
          <MatchScoreboard
            homeGoals={homeGoals}
            awayGoals={awayGoals}
            status={status}
            size="lg"
          />
          <div className="flex justify-center">
            <LargeTeamFlag team={awayTeam} />
          </div>
        </div>
        <div className="match-card-teams__row match-card-teams__names gap-x-3 sm:gap-x-6 md:gap-x-10">
          <p className="mx-auto max-w-[7rem] text-center font-display type-title text-base sm:max-w-[10rem] sm:text-lg md:max-w-none md:text-xl">
            {stripDisplayDashes(homeTeam.name)}
          </p>
          <span aria-hidden="true" />
          <p className="mx-auto max-w-[7rem] text-center font-display type-title text-base sm:max-w-[10rem] sm:text-lg md:max-w-none md:text-xl">
            {stripDisplayDashes(awayTeam.name)}
          </p>
        </div>
      </div>

      {venue && (
        <p className="mt-4 text-center text-sm text-muted">{stripDisplayDashes(venue)}</p>
      )}
    </header>
  );
}
