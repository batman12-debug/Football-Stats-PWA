import {
  formatMatchDate,
  formatMatchMinute,
  isFinishedStatus,
  isLiveStatus,
  PKT_OFFSET_MS,
} from "@/lib/utils";
import type { PinEntry } from "./types";

export const NOTIFICATION_APP_NAME = "CheckBoard";

export interface LiveScoreSnapshot {
  status: string;
  isLive: boolean;
  minute: number;
  homeGoals: number | null;
  awayGoals: number | null;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;

function toPktParts(ms: number) {
  const pkt = new Date(ms + PKT_OFFSET_MS);
  return {
    y: pkt.getUTCFullYear(),
    m: pkt.getUTCMonth(),
    d: pkt.getUTCDate(),
    weekday: WEEKDAYS[pkt.getUTCDay()],
    hours24: pkt.getUTCHours(),
    minutes: pkt.getUTCMinutes(),
  };
}

function formatTimePkt(hours24: number, minutes: number): string {
  const ampm = hours24 >= 12 ? "PM" : "AM";
  const hours12 = hours24 % 12 || 12;
  const minuteStr = minutes.toString().padStart(2, "0");
  return `${hours12}:${minuteStr} ${ampm}`;
}

/** Center stack for the rich card — matches the reference (Tomorrow / 12:00 AM). */
export function formatKickoffCenterLines(
  kickoffIso: string,
  nowMs: number = Date.now()
): { primary: string; secondary: string } {
  const kick = new Date(kickoffIso);
  if (Number.isNaN(kick.getTime())) {
    return { primary: "Upcoming", secondary: kickoffIso };
  }

  const now = toPktParts(nowMs);
  const target = toPktParts(kick.getTime());
  const time = formatTimePkt(target.hours24, target.minutes);

  const startOfToday = Date.UTC(now.y, now.m, now.d) - PKT_OFFSET_MS;
  const startOfTarget = Date.UTC(target.y, target.m, target.d) - PKT_OFFSET_MS;
  const dayDiff = Math.round((startOfTarget - startOfToday) / (24 * 60 * 60 * 1000));

  if (dayDiff === 0) return { primary: "Today", secondary: time };
  if (dayDiff === 1) return { primary: "Tomorrow", secondary: time };
  if (dayDiff === -1) return { primary: "Yesterday", secondary: time };
  return { primary: target.weekday, secondary: time };
}

export function formatCenterLinesForSnapshot(
  entry: PinEntry,
  snapshot: LiveScoreSnapshot | null,
  nowMs: number = Date.now()
): { primary: string; secondary: string } {
  if (snapshot && (snapshot.isLive || isLiveStatus(snapshot.status))) {
    const minute =
      formatMatchMinute(snapshot.minute, snapshot.status) ??
      (snapshot.minute > 0 ? `${snapshot.minute}'` : "LIVE");
    return { primary: "LIVE", secondary: minute };
  }

  if (snapshot && isFinishedStatus(snapshot.status)) {
    const hg = snapshot.homeGoals ?? 0;
    const ag = snapshot.awayGoals ?? 0;
    return { primary: "FT", secondary: `${hg}–${ag}` };
  }

  return formatKickoffCenterLines(entry.kickoffIso, nowMs);
}

/**
 * Notification chrome: brand as title; body is a text fallback for
 * platforms that do not render the rich `image` card.
 */
export function formatLiveScoreNotification(
  entry: PinEntry,
  snapshot: LiveScoreSnapshot | null,
  nowMs: number = Date.now()
): { title: string; body: string } {
  const title = NOTIFICATION_APP_NAME;
  const center = formatCenterLinesForSnapshot(entry, snapshot, nowMs);

  if (
    !snapshot ||
    (!snapshot.isLive && !isLiveStatus(snapshot.status) && !isFinishedStatus(snapshot.status))
  ) {
    return {
      title,
      body: `${entry.homeName} vs ${entry.awayName} · ${center.primary} ${center.secondary}`,
    };
  }

  const hg = snapshot.homeGoals ?? 0;
  const ag = snapshot.awayGoals ?? 0;

  if (isFinishedStatus(snapshot.status)) {
    return {
      title,
      body: `${entry.homeName} ${hg}–${ag} ${entry.awayName} · FT`,
    };
  }

  const minute =
    formatMatchMinute(snapshot.minute, snapshot.status) ??
    (snapshot.minute > 0 ? `${snapshot.minute}'` : "");
  return {
    title,
    body: `${entry.homeName} ${hg}–${ag} ${entry.awayName}${minute ? ` · ${minute}` : ""}`,
  };
}

/** Kept for call sites that still want the long kickoff string. */
export function formatUpcomingKickoffLabel(kickoffIso: string): string {
  return formatMatchDate(kickoffIso);
}
