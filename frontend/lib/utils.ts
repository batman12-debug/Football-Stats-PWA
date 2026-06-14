/** Shared formatting and UI helpers. */

import type { ConfidenceLevel } from "@/types";

/** Remove dash characters from user visible copy. */
export function stripDisplayDashes(text: string): string {
  return text
    .replace(/[\u2010-\u2015\u2212-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function formatMatchScore(homeGoals: number, awayGoals: number): string {
  return `${homeGoals} - ${awayGoals}`;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;

/** Pakistan Standard Time — fixed UTC+5, no daylight saving. */
export const PKT_OFFSET_MS = 5 * 60 * 60 * 1000;
export const PKT_LABEL = "PKT";

function toPktWallClock(date: Date): Date {
  return new Date(date.getTime() + PKT_OFFSET_MS);
}

/** Deterministic PKT formatting — avoids server/client Intl locale drift. */
export function formatMatchDate(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;

  const pkt = toPktWallClock(date);
  const weekday = WEEKDAYS[pkt.getUTCDay()];
  const month = MONTHS[pkt.getUTCMonth()];
  const day = pkt.getUTCDate();
  const hours24 = pkt.getUTCHours();
  const minutes = pkt.getUTCMinutes();
  const ampm = hours24 >= 12 ? "PM" : "AM";
  const hours12 = hours24 % 12 || 12;
  const minuteStr = minutes.toString().padStart(2, "0");

  return `${weekday}, ${month} ${day} at ${hours12}:${minuteStr} ${ampm} ${PKT_LABEL}`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatGoals(value: number): string {
  return value.toFixed(1);
}

export function getConfidenceLevel(score: number): ConfidenceLevel {
  if (score >= 0.7) return "high";
  if (score >= 0.4) return "medium";
  return "low";
}

export function getConfidenceLabel(level: ConfidenceLevel): string {
  return level.charAt(0).toUpperCase() + level.slice(1);
}

export function formToDisplay(form: string | null, recentForm: number): string {
  if (form) return form.slice(-5).toUpperCase();
  return formatPercent(recentForm);
}

const LIVE_STATUSES = new Set(["LIVE", "1H", "2H", "HT", "ET", "BT", "P", "INT"]);
const FINISHED_STATUSES = new Set(["FT", "AET", "PEN"]);

export function isLiveStatus(status: string): boolean {
  return LIVE_STATUSES.has(status);
}

export function isFinishedStatus(status: string): boolean {
  return FINISHED_STATUSES.has(status);
}

export function hasScoreboard(
  homeGoals: number | null,
  awayGoals: number | null,
): boolean {
  return homeGoals !== null && awayGoals !== null;
}

export function formatStatusLabel(status: string): string {
  if (isLiveStatus(status)) return "LIVE";
  return status;
}

/** Format live match minute with stoppage time (e.g. 45+2', 90+3'). */
export function formatMatchMinute(
  minute: number | null | undefined,
  status?: string,
): string | null {
  if (minute == null || minute < 0 || Number.isNaN(minute)) return null;

  const normalizedStatus = status?.toUpperCase() ?? "";
  const inFirstHalf = normalizedStatus === "1H";
  const inSecondHalf = normalizedStatus === "2H";

  const concatenated = parseConcatenatedStoppageMinute(minute);
  if (concatenated) {
    return `${concatenated.base}+${concatenated.extra}'`;
  }

  if (inFirstHalf && minute > 45) {
    return `45+${minute - 45}'`;
  }

  if ((inSecondHalf || minute > 90) && minute > 90) {
    return `90+${minute - 90}'`;
  }

  return `${minute}'`;
}

/** Recover stoppage labels when "+" was stripped (e.g. 453 → 45+3). */
function parseConcatenatedStoppageMinute(
  minute: number,
): { base: number; extra: number } | null {
  if (minute >= 451 && minute <= 459) {
    return { base: 45, extra: minute - 450 };
  }
  if (minute >= 901 && minute <= 920) {
    return { base: 90, extra: minute - 900 };
  }
  return null;
}
