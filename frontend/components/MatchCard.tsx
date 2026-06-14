"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { MiniPredictionBar } from "@/components/MiniPredictionBar";
import { MatchScoreboard } from "@/components/MatchScoreboard";
import { TeamFlagGlow } from "@/components/TeamFlagGlow";
import { isQatarTeam } from "@/lib/isQatarTeam";
import type { MatchWithPrediction } from "@/types";
import { formatMatchDate, isLiveStatus, stripDisplayDashes } from "@/lib/utils";

interface MatchCardProps {
  match: MatchWithPrediction;
  compact?: boolean;
  showMatchNumber?: boolean;
}

function TeamBadge({
  name,
  code,
  logo,
  isPlaceholder,
}: {
  name: string;
  code: string | null;
  logo: string | null;
  isPlaceholder?: boolean;
}) {
  if (!isPlaceholder && isQatarTeam({ name, code })) {
    return (
      <div className="flex flex-col items-center gap-2 text-center">
        <TeamFlagGlow team={{ name, code, logo }} size="md" />
        <span className="max-w-[6rem] truncate text-xs type-ui sm:max-w-[7rem] sm:text-sm">
          {stripDisplayDashes(name)}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div
        className={`relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-full sm:h-12 sm:w-12 ${
          isPlaceholder ? "border border-dashed border-muted bg-transparent" : "bg-card-border"
        }`}
      >
        {logo ? (
          <Image
            src={logo}
            alt={`${name} flag`}
            width={48}
            height={48}
            className="h-full w-full object-cover"
          />
        ) : (
          <span className={`text-xs font-bold ${isPlaceholder ? "text-muted" : ""}`}>
            {isPlaceholder ? "?" : (code ?? name.slice(0, 3)).toUpperCase()}
          </span>
        )}
      </div>
      <span
        className={`max-w-[6rem] truncate text-xs type-ui sm:max-w-[7rem] sm:text-sm ${
          isPlaceholder ? "text-muted" : ""
        }`}
      >
        {stripDisplayDashes(name)}
      </span>
    </div>
  );
}

export function MatchCard({ match, compact = false, showMatchNumber = false }: MatchCardProps) {
  const router = useRouter();
  const { home_team, away_team, prediction } = match;
  const canNavigate =
    !home_team.is_placeholder &&
    !away_team.is_placeholder &&
    match.home_team.id > 0 &&
    match.away_team.id > 0;
  const isLive = isLiveStatus(match.status);
  const matchHref = `/match/${match.id}`;

  useEffect(() => {
    if (isLive && canNavigate) {
      router.prefetch(matchHref);
    }
  }, [isLive, canNavigate, matchHref, router]);

  const content = (
    <article
      className={`flex h-full flex-col gap-3 rounded-xl border bg-card transition-colors ${
        compact ? "p-3" : "gap-4 p-4"
      } ${
        isLive
          ? "border-loss/40 ring-1 ring-loss/20"
          : "border-card-border"
      } ${canNavigate ? "group-hover:border-win/30" : "opacity-90"}`}
    >
      <div className="type-caps flex items-center justify-center gap-2 text-center text-xs text-muted">
        {showMatchNumber && match.match_number && (
          <span className="rounded bg-card-border px-1.5 py-0.5 text-[10px]">
            M{match.match_number}
          </span>
        )}
        <span>{formatMatchDate(match.date)}</span>
      </div>

      <div className="flex items-center justify-between gap-2">
        <TeamBadge
          name={home_team.name}
          code={home_team.code}
          logo={home_team.logo}
          isPlaceholder={home_team.is_placeholder}
        />
        <MatchScoreboard
          homeGoals={match.home_goals}
          awayGoals={match.away_goals}
          status={match.status}
        />
        <TeamBadge
          name={away_team.name}
          code={away_team.code}
          logo={away_team.logo}
          isPlaceholder={away_team.is_placeholder}
        />
      </div>

      {prediction && canNavigate ? (
        <MiniPredictionBar
          homeWin={prediction.home_win_probability}
          draw={prediction.draw_probability}
          awayWin={prediction.away_win_probability}
          homeName={home_team.name}
          awayName={away_team.name}
        />
      ) : !canNavigate ? (
        <p className="text-center text-[10px] text-muted">Awaiting qualified teams</p>
      ) : null}

      {match.venue && !compact && (
        <p className="truncate text-center text-xs text-muted">{stripDisplayDashes(match.venue)}</p>
      )}
    </article>
  );

  if (!canNavigate) {
    return <div className="block h-full">{content}</div>;
  }

  return (
    <Link href={matchHref} prefetch className="group block h-full">
      {content}
    </Link>
  );
}
