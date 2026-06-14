"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";

import { GoogleStyleTeamStats } from "@/components/GoogleStyleTeamStats";
import { TeamSquadPanel, TeamSquadSkeleton } from "@/components/TeamSquadPanel";
import { fetchTeamSquadClient, fetchTeamStatsClient } from "@/lib/api";
import {
  GROUP_ORDER,
  buildTeamGroupMap,
  findStandingForTeam,
  getTeamGroup,
  sortTeams,
} from "@/lib/teams";
import type { TeamSquad, TeamStats, TeamSummary, TournamentBracket } from "@/types";
import { stripDisplayDashes } from "@/lib/utils";

interface TeamsViewProps {
  teams: TeamSummary[];
  bracket: TournamentBracket | null;
}

export function TeamsView({ teams, bracket }: TeamsViewProps) {
  const groupMap = useMemo(() => buildTeamGroupMap(bracket), [bracket]);
  const sortedTeams = useMemo(() => sortTeams(teams, groupMap), [teams, groupMap]);

  const [query, setQuery] = useState("");
  const [groupFilter, setGroupFilter] = useState<string>("all");
  const [selectedId, setSelectedId] = useState<number | null>(sortedTeams[0]?.id ?? null);
  const [stats, setStats] = useState<TeamStats | null>(null);
  const [squad, setSquad] = useState<TeamSquad | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [loadingSquad, setLoadingSquad] = useState(false);

  const selectedTeam = sortedTeams.find((team) => team.id === selectedId) ?? null;

  const filteredTeams = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sortedTeams.filter((team) => {
      const group = getTeamGroup(team, groupMap);
      if (groupFilter !== "all" && group !== groupFilter) return false;
      if (!q) return true;
      return (
        team.name.toLowerCase().includes(q) ||
        (team.code?.toLowerCase().includes(q) ?? false) ||
        (group?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [sortedTeams, groupMap, query, groupFilter]);

  const loadTeamDetails = useCallback(async (teamId: number) => {
    setLoadingStats(true);
    setLoadingSquad(true);
    setStats(null);
    setSquad(null);

    const [statsData, squadData] = await Promise.all([
      fetchTeamStatsClient(teamId),
      fetchTeamSquadClient(teamId),
    ]);

    setStats(statsData);
    setSquad(squadData);
    setLoadingStats(false);
    setLoadingSquad(false);
  }, []);

  useEffect(() => {
    if (selectedId !== null) {
      void loadTeamDetails(selectedId);
    }
  }, [selectedId, loadTeamDetails]);

  useEffect(() => {
    const shouldPoll =
      selectedId !== null &&
      (squad?.is_live_lineup || (squad !== null && !squad.lineup_confirmed));

    if (!shouldPoll) {
      return;
    }

    const intervalMs = squad?.is_live_lineup ? 30_000 : 120_000;

    const interval = setInterval(() => {
      void fetchTeamSquadClient(selectedId).then((data) => {
        if (data) setSquad(data);
      });
    }, intervalMs);

    return () => clearInterval(interval);
  }, [squad?.is_live_lineup, squad?.lineup_confirmed, selectedId]);

  const standing = selectedTeam
    ? findStandingForTeam(bracket, selectedTeam.name)
    : null;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,340px)_1fr] lg:items-start">
      {/* Left: search + team list (Google sidebar pattern) */}
      <aside className="space-y-4 lg:sticky lg:top-6">
        <div className="relative">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search teams"
            className="w-full rounded-full border border-card-border bg-card py-3 pl-4 pr-4 text-base text-white outline-none transition-colors placeholder:text-muted focus:border-win/50 focus:ring-1 focus:ring-win/30 sm:py-2.5 sm:text-sm"
            aria-label="Search teams"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <FilterChip
            active={groupFilter === "all"}
            onClick={() => setGroupFilter("all")}
            label="All"
          />
          {GROUP_ORDER.map((group) => (
            <FilterChip
              key={group}
              active={groupFilter === group}
              onClick={() => setGroupFilter(group)}
              label={group.replace("Group ", "")}
            />
          ))}
        </div>

        <ul className="max-h-[28rem] space-y-1 overflow-y-auto rounded-xl border border-card-border bg-card p-2 lg:max-h-[calc(100vh-12rem)]">
          {filteredTeams.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-muted">No teams found</li>
          ) : (
            filteredTeams.map((team) => {
              const group = getTeamGroup(team, groupMap);
              const isSelected = team.id === selectedId;

              return (
                <li key={team.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(team.id)}
                    className={`flex w-full min-h-11 items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors sm:py-2.5 ${
                      isSelected
                        ? "bg-win/10 ring-1 ring-win/30"
                        : "hover:bg-card-border/40"
                    }`}
                  >
                    <TeamFlag team={team} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{stripDisplayDashes(team.name)}</p>
                      {group && (
                        <p className="truncate text-xs text-muted">{group}</p>
                      )}
                    </div>
                  </button>
                </li>
              );
            })
          )}
        </ul>
      </aside>

      {/* Right: team detail panel */}
      <div className="min-w-0 space-y-6">
        {!selectedTeam ? (
          <div className="rounded-2xl border border-card-border bg-card p-10 text-center text-muted">
            Select a team to view stats and squad
          </div>
        ) : (
          <>
            {loadingStats ? (
              <TeamStatsSkeleton team={selectedTeam} group={getTeamGroup(selectedTeam, groupMap)} />
            ) : stats ? (
              <GoogleStyleTeamStats
                team={selectedTeam}
                stats={stats}
                group={getTeamGroup(selectedTeam, groupMap)}
                standing={standing}
              />
            ) : (
              <div className="rounded-2xl border border-card-border bg-card p-10 text-center">
                <p className="font-medium">Stats unavailable</p>
                <p className="mt-2 text-sm text-muted">
                  Could not load data for {stripDisplayDashes(selectedTeam.name)}. Ensure the backend is running.
                </p>
              </div>
            )}

            {loadingSquad ? (
              <TeamSquadSkeleton teamName={stripDisplayDashes(selectedTeam.name)} />
            ) : squad ? (
              <TeamSquadPanel squad={squad} />
            ) : (
              <div className="rounded-2xl border border-card-border bg-card p-8 text-center text-sm text-muted">
                Squad data unavailable for {stripDisplayDashes(selectedTeam.name)}.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-9 rounded-full px-3.5 py-2 text-xs font-medium transition-colors ${
        active
          ? "bg-win/15 text-win ring-1 ring-win/30"
          : "bg-card text-muted ring-1 ring-card-border hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}

function TeamFlag({ team, size }: { team: TeamSummary; size: "sm" | "md" }) {
  const dim = size === "sm" ? "h-8 w-8" : "h-10 w-10";

  return (
    <div
      className={`relative shrink-0 overflow-hidden rounded-full border border-card-border bg-card-border ${dim}`}
    >
      {team.logo ? (
        <Image
          src={team.logo}
          alt=""
          width={40}
          height={40}
          className="h-full w-full object-cover"
        />
      ) : (
        <span className="flex h-full w-full items-center justify-center text-[10px] font-bold text-muted">
          {(team.code ?? team.name.slice(0, 2)).toUpperCase()}
        </span>
      )}
    </div>
  );
}

function TeamStatsSkeleton({
  team,
  group,
}: {
  team: TeamSummary;
  group: string | null;
}) {
  return (
    <div className="animate-pulse overflow-hidden rounded-2xl border border-card-border bg-card">
      <div className="border-b border-card-border px-6 py-5">
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 rounded-full bg-card-border" />
          <div className="space-y-2">
            <div className="h-7 w-40 rounded bg-card-border" />
            <div className="h-4 w-56 rounded bg-card-border" />
            {group && <div className="h-3 w-24 rounded bg-card-border" />}
          </div>
        </div>
      </div>
      <div className="space-y-4 p-6">
        <div className="h-4 w-28 rounded bg-card-border" />
        <div className="flex gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 w-8 rounded-full bg-card-border" />
          ))}
        </div>
        <div className="grid grid-cols-4 gap-px rounded-xl bg-card-border">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-card" />
          ))}
        </div>
        <p className="text-center text-xs text-muted">Loading {stripDisplayDashes(team.name)}…</p>
      </div>
    </div>
  );
}
