/** Tournament fixture collection and date filtering. */

import type { BracketFixture, TournamentBracket, TournamentStageSection } from "@/types";
import { PKT_OFFSET_MS } from "@/lib/utils";

export const TOMORROW_VIEW = "tomorrow";

export const TOURNAMENT_STAGES = [
  { value: "group_stage", label: "Group Stage" },
  { value: "round_of_32", label: "Round of 32" },
  { value: "round_of_16", label: "Round of 16" },
  { value: "quarter_final", label: "Quarter-finals" },
  { value: "semi_final", label: "Semi-finals" },
  { value: "third_place", label: "Third Place Play-off" },
  { value: "final", label: "Final" },
] as const;

export function matchesViewHref(view: string): string {
  if (!view || view === TOMORROW_VIEW) {
    return "/matches?view=tomorrow";
  }
  return `/matches?view=${encodeURIComponent(view)}`;
}

export function parseMatchesView(rawView: string | null): string {
  if (!rawView || rawView === TOMORROW_VIEW) {
    return TOMORROW_VIEW;
  }
  const allowed = new Set<string>([
    TOMORROW_VIEW,
    ...TOURNAMENT_STAGES.map((stage) => stage.value),
  ]);
  return allowed.has(rawView) ? rawView : TOMORROW_VIEW;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;

export function pktDateKey(isoDate: string): string {
  const date = new Date(isoDate);
  const pkt = new Date(date.getTime() + PKT_OFFSET_MS);
  const y = pkt.getUTCFullYear();
  const m = String(pkt.getUTCMonth() + 1).padStart(2, "0");
  const d = String(pkt.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Calendar date for tomorrow in PKT (UTC fields hold PKT components). */
export function getTomorrowPkt(): Date {
  const now = new Date();
  const pktNow = new Date(now.getTime() + PKT_OFFSET_MS);
  return new Date(
    Date.UTC(pktNow.getUTCFullYear(), pktNow.getUTCMonth(), pktNow.getUTCDate() + 1)
  );
}

export function formatDayLabel(date: Date): string {
  const weekday = WEEKDAYS[date.getUTCDay()];
  const month = MONTHS[date.getUTCMonth()];
  const day = date.getUTCDate();
  return `${weekday}, ${month} ${day}`;
}

function pktCalendarKey(date: Date): string {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function collectStageFixtures(stage: TournamentStageSection): BracketFixture[] {
  const fixtures: BracketFixture[] = [];

  if (stage.groups) {
    for (const group of stage.groups) {
      fixtures.push(...group.fixtures);
    }
  }

  fixtures.push(...stage.fixtures);
  fixtures.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  return fixtures;
}

export function collectAllFixtures(bracket: TournamentBracket): BracketFixture[] {
  return bracket.stages.flatMap(collectStageFixtures);
}

export function filterFixturesForTomorrow(
  fixtures: BracketFixture[],
  tomorrow: Date = getTomorrowPkt()
): BracketFixture[] {
  const key = pktCalendarKey(tomorrow);
  return fixtures
    .filter((fixture) => pktDateKey(fixture.date) === key)
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}

export function findStage(
  bracket: TournamentBracket,
  stageKey: string
): TournamentStageSection | undefined {
  return bracket.stages.find((stage) => stage.stage === stageKey);
}
