/** Team list helpers — group mapping from bracket data. */

import type { GroupStandingRow, TeamSummary, TournamentBracket } from "@/types";

export function buildTeamGroupMap(bracket: TournamentBracket | null): Map<string, string> {
  const map = new Map<string, string>();
  if (!bracket) return map;

  const groupStage = bracket.stages.find((stage) => stage.stage === "group_stage");
  if (!groupStage?.groups) return map;

  for (const group of groupStage.groups) {
    for (const row of group.standings) {
      map.set(normalizeTeamKey(row.team), group.group);
    }
    for (const fixture of group.fixtures) {
      map.set(normalizeTeamKey(fixture.home_team.name), group.group);
      map.set(normalizeTeamKey(fixture.away_team.name), group.group);
    }
  }

  return map;
}

export function normalizeTeamKey(name: string): string {
  return name.trim().toLowerCase();
}

export function getTeamGroup(
  team: TeamSummary,
  groupMap: Map<string, string>
): string | null {
  return groupMap.get(normalizeTeamKey(team.name)) ?? null;
}

export function findStandingForTeam(
  bracket: TournamentBracket | null,
  teamName: string
): GroupStandingRow | null {
  if (!bracket) return null;

  const groupStage = bracket.stages.find((stage) => stage.stage === "group_stage");
  if (!groupStage?.groups) return null;

  const key = normalizeTeamKey(teamName);
  for (const group of groupStage.groups) {
    const row = group.standings.find((s) => normalizeTeamKey(s.team) === key);
    if (row) return row;
  }

  return null;
}

export const GROUP_ORDER = [
  "Group A", "Group B", "Group C", "Group D", "Group E", "Group F",
  "Group G", "Group H", "Group I", "Group J", "Group K", "Group L",
] as const;

export function sortTeams(teams: TeamSummary[], groupMap: Map<string, string>): TeamSummary[] {
  return [...teams].sort((a, b) => {
    const groupA = getTeamGroup(a, groupMap) ?? "Group Z";
    const groupB = getTeamGroup(b, groupMap) ?? "Group Z";
    const groupCompare = groupA.localeCompare(groupB);
    if (groupCompare !== 0) return groupCompare;
    return a.name.localeCompare(b.name);
  });
}
