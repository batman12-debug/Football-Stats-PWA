"use client";

import Image from "next/image";

import type { PlayerSummary, SquadCategory, TeamSquad } from "@/types";
import { stripDisplayDashes } from "@/lib/utils";
import { formatMatchMinute } from "@/lib/utils";

interface TeamSquadPanelProps {
  squad: TeamSquad;
}

const SECTIONS: {
  key: keyof Pick<TeamSquad, "starting_xi" | "substitutes" | "reserves" | "injured">;
  title: string;
  liveTitle?: string;
  description: string;
  liveDescription?: string;
  accent: string;
}[] = [
  {
    key: "starting_xi",
    title: "Starting XI",
    liveTitle: "On the pitch",
    description: "Projected first choice lineup",
    liveDescription: "Players currently on the field",
    accent: "text-win",
  },
  {
    key: "substitutes",
    title: "Substitutes",
    description: "Matchday bench players",
    accent: "text-white",
  },
  {
    key: "reserves",
    title: "Reserve players",
    description: "Extended squad outside the matchday 23",
    accent: "text-muted",
  },
  {
    key: "injured",
    title: "Injured",
    description: "Currently unavailable",
    accent: "text-loss",
  },
];

function categoryLabel(category: SquadCategory): string {
  switch (category) {
    case "starting":
      return "Starter";
    case "substitute":
      return "Sub";
    case "reserve":
      return "Reserve";
    case "injured":
      return "Injured";
    default:
      return category;
  }
}

function PlayerAvatar({ player }: { player: PlayerSummary }) {
  return (
    <div className="relative h-12 w-12 shrink-0">
      <div className="relative flex h-12 w-12 items-center justify-center overflow-hidden rounded-full border-2 border-card-border bg-card-border">
        {player.photo ? (
          <Image
            src={player.photo}
            alt=""
            width={48}
            height={48}
            className="h-full w-full object-cover"
            unoptimized
          />
        ) : (
          <span className="text-xs font-bold text-muted">
            {(player.name.split(" ").map((part) => part[0]).join("").slice(0, 2) || "?").toUpperCase()}
          </span>
        )}
      </div>
      {player.number !== null && (
        <span className="absolute -bottom-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full border border-card-border bg-background px-1 text-[10px] font-bold tabular-nums text-win">
          {player.number}
        </span>
      )}
    </div>
  );
}

function PlayerRow({ player }: { player: PlayerSummary }) {
  return (
    <li className="flex items-center gap-3 rounded-lg px-2 py-2.5 transition-colors hover:bg-card-border/30">
      <PlayerAvatar player={player} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{stripDisplayDashes(player.name)}</p>
        <p className="truncate text-xs text-muted">
          {player.position ?? "Player"}
          {player.injury_reason ? ` · ${stripDisplayDashes(player.injury_reason)}` : ""}
        </p>
      </div>
      <span className="shrink-0 text-[10px] font-medium uppercase tracking-wide text-muted">
        {categoryLabel(player.category)}
      </span>
    </li>
  );
}

function SquadSection({
  title,
  description,
  accent,
  players,
  emptyMessage,
}: {
  title: string;
  description: string;
  accent: string;
  players: PlayerSummary[];
  emptyMessage?: string;
}) {
  if (players.length === 0) {
    if (!emptyMessage) {
      return null;
    }

    return (
      <section>
        <div className="mb-3">
          <h3 className={`text-sm font-semibold ${accent}`}>{title}</h3>
          <p className="text-xs text-muted">{description}</p>
        </div>
        <p className="rounded-xl border border-dashed border-card-border px-4 py-6 text-center text-sm text-muted">
          {emptyMessage}
        </p>
      </section>
    );
  }

  return (
    <section>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h3 className={`text-sm font-semibold ${accent}`}>{title}</h3>
          <p className="text-xs text-muted">{description}</p>
        </div>
        <span className="text-xs font-medium tabular-nums text-muted">{players.length}</span>
      </div>
      <ul className="divide-y divide-card-border/60 rounded-xl border border-card-border">
        {players.map((player) => (
          <PlayerRow key={player.id} player={player} />
        ))}
      </ul>
    </section>
  );
}

export function TeamSquadPanel({ squad }: TeamSquadPanelProps) {
  const isLive = squad.is_live_lineup;
  const lineupConfirmed = squad.lineup_confirmed;

  return (
    <article className="overflow-hidden rounded-2xl border border-card-border bg-card">
      <header className="border-b border-card-border px-5 py-5 sm:px-6">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">World Cup squad</h2>
          {isLive && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-loss/15 px-2.5 py-0.5 text-xs font-semibold text-loss">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-loss" />
              Live {squad.live_minute !== null ? formatMatchMinute(squad.live_minute) ?? "" : ""}
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-muted">
          {squad.all_players.length} players · {stripDisplayDashes(squad.team_name)}
          {squad.source === "espn"
            ? lineupConfirmed
              ? " · Confirmed lineup"
              : " · Squad roster"
            : squad.source === "statsbomb"
              ? " · World Cup squad data"
              : ""}
        </p>
      </header>

      <div className="space-y-6 px-5 py-5 sm:px-6">
        <section>
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted">
            All players
          </h3>
          <ul className="grid gap-2 sm:grid-cols-2">
            {squad.all_players.map((player) => (
              <PlayerRow key={`all-${player.id}`} player={player} />
            ))}
          </ul>
        </section>

        {SECTIONS.map((section) => (
          <SquadSection
            key={section.key}
            title={
              isLive && section.key === "starting_xi" && section.liveTitle
                ? section.liveTitle
                : section.title
            }
            description={
              isLive && section.key === "starting_xi" && section.liveDescription
                ? section.liveDescription
                : section.key === "starting_xi" && !lineupConfirmed
                  ? "Announced before kickoff"
                  : section.description
            }
            accent={section.accent}
            players={squad[section.key]}
            emptyMessage={
              section.key === "starting_xi" && !lineupConfirmed
                ? "Starting XI will appear here once the lineup is announced, usually about an hour before kickoff."
                : undefined
            }
          />
        ))}
      </div>
    </article>
  );
}

export function TeamSquadSkeleton({ teamName }: { teamName: string }) {
  return (
    <div className="animate-pulse overflow-hidden rounded-2xl border border-card-border bg-card">
      <div className="border-b border-card-border px-6 py-5">
        <div className="h-6 w-40 rounded bg-card-border" />
        <div className="mt-2 h-4 w-56 rounded bg-card-border" />
      </div>
      <div className="space-y-3 p-6">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="h-14 rounded-lg bg-card-border/60" />
        ))}
        <p className="text-center text-xs text-muted">Loading {teamName} squad…</p>
      </div>
    </div>
  );
}
