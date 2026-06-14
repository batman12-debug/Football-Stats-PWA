/**
 * Fetch wrapper for GoalMind backend API.
 *
 * Server components call the backend directly via API_URL.
 * Browser code uses same-origin /api/* (proxied by app/api/[...path]/route.ts).
 */

import type {
  BracketFixture,
  FixtureDetail,
  FixtureSummary,
  MatchWithPrediction,
  Prediction,
  LiveMatchStats,
  NewsFeedResponse,
  TeamSquad,
  TeamStats,
  TeamSummary,
  TournamentBracket,
} from "@/types";

const REVALIDATE_SECONDS = 300;
const FETCH_TIMEOUT_MS = 30_000;
const MATCH_DETAIL_TIMEOUT_MS = 8_000;

type FetchFromApiOptions = {
  revalidate?: number | false;
  timeoutMs?: number;
};

function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export async function fetchFromApi<T>(
  endpoint: string,
  options?: FetchFromApiOptions,
): Promise<T | null> {
  const timeoutMs = options?.timeoutMs ?? FETCH_TIMEOUT_MS;
  const revalidate = options?.revalidate ?? REVALIDATE_SECONDS;
  const cacheMode =
    revalidate === false
      ? ({ cache: "no-store" } as const)
      : ({ next: { revalidate } } as const);

  try {
    const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
      headers: { "Content-Type": "application/json" },
      ...cacheMode,
      signal: AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getTournamentBracket(): Promise<TournamentBracket | null> {
  return fetchFromApi<TournamentBracket>("/api/matches/bracket");
}

export async function fetchTournamentBracketClient(): Promise<TournamentBracket | null> {
  try {
    const response = await fetch("/api/matches/bracket", {
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
    if (!response.ok) return null;
    return (await response.json()) as TournamentBracket;
  } catch {
    return null;
  }
}

export async function getTeams(): Promise<TeamSummary[]> {
  const teams = await fetchFromApi<TeamSummary[]>("/api/teams");
  return teams ?? [];
}

export async function getTeamStats(teamId: number): Promise<TeamStats | null> {
  return fetchFromApi<TeamStats>(`/api/teams/${teamId}/stats`);
}

/** Client-side stats fetch (for interactive team selection). */
export async function fetchTeamStatsClient(teamId: number): Promise<TeamStats | null> {
  try {
    const response = await fetch(`/api/teams/${teamId}/stats`, {
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
    if (!response.ok) return null;
    return (await response.json()) as TeamStats;
  } catch {
    return null;
  }
}

export async function fetchTeamSquadClient(teamId: number): Promise<TeamSquad | null> {
  try {
    const response = await fetch(`/api/teams/${teamId}/squad`, {
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
    if (!response.ok) return null;
    return (await response.json()) as TeamSquad;
  } catch {
    return null;
  }
}

export async function getNewsFeed(category?: string): Promise<NewsFeedResponse | null> {
  const query = category && category !== "All" ? `?category=${encodeURIComponent(category)}` : "";
  return fetchFromApi<NewsFeedResponse>(`/api/news${query}`);
}

export async function fetchNewsFeedClient(category?: string): Promise<NewsFeedResponse | null> {
  try {
    const query = category && category !== "All" ? `?category=${encodeURIComponent(category)}` : "";
    const response = await fetch(`/api/news${query}`, {
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
    if (!response.ok) return null;
    return (await response.json()) as NewsFeedResponse;
  } catch {
    return null;
  }
}

export async function getUpcomingMatches(): Promise<FixtureSummary[]> {
  const matches = await fetchFromApi<FixtureSummary[]>("/api/matches/upcoming");
  return matches ?? [];
}

export async function getMatchDetail(fixtureId: string): Promise<FixtureDetail | null> {
  return fetchFromApi<FixtureDetail>(`/api/matches/${fixtureId}`, {
    revalidate: false,
    timeoutMs: MATCH_DETAIL_TIMEOUT_MS,
  });
}

export async function fetchLiveMatchStats(fixtureId: string): Promise<LiveMatchStats | null> {
  try {
    const response = await fetch(`/api/matches/${fixtureId}/live-stats`, {
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) return null;
    return (await response.json()) as LiveMatchStats;
  } catch {
    return null;
  }
}

export async function getPrediction(fixtureId: string): Promise<Prediction | null> {
  return fetchFromApi<Prediction>(`/api/predictions/${fixtureId}`);
}

export async function getUpcomingMatchesWithPredictions(): Promise<MatchWithPrediction[]> {
  const matches = await getUpcomingMatches();
  if (matches.length === 0) return [];

  const predictions = await Promise.all(
    matches.map((match) => getPrediction(String(match.id)))
  );

  return matches.map((match, index) => ({
    ...match,
    prediction: predictions[index],
  }));
}

export async function getMatchWithPrediction(fixtureId: string): Promise<{
  match: FixtureDetail | null;
  prediction: Prediction | null;
}> {
  const [match, prediction] = await Promise.all([
    getMatchDetail(fixtureId),
    getPrediction(fixtureId),
  ]);

  return { match, prediction };
}
