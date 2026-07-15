import { formatMatchDate, isFinishedStatus, isLiveStatus } from "@/lib/utils";
import type { PinEntry } from "./types";

export interface LiveScoreSnapshot {
  status: string;
  isLive: boolean;
  minute: number;
  homeGoals: number | null;
  awayGoals: number | null;
}

function teamLabel(code: string | null, name: string): string {
  return (code ?? name.slice(0, 3)).toUpperCase();
}

export function formatLiveScoreNotification(
  entry: PinEntry,
  snapshot: LiveScoreSnapshot | null
): { title: string; body: string } {
  const home = teamLabel(entry.homeCode, entry.homeName);
  const away = teamLabel(entry.awayCode, entry.awayName);
  const title = `${home} vs ${away}`;

  if (!snapshot || (!snapshot.isLive && !isLiveStatus(snapshot.status) && !isFinishedStatus(snapshot.status))) {
    return {
      title,
      body: `Upcoming · ${formatMatchDate(entry.kickoffIso)}`,
    };
  }

  const hg = snapshot.homeGoals ?? 0;
  const ag = snapshot.awayGoals ?? 0;
  const score = `${home} ${hg}–${ag} ${away}`;

  if (isFinishedStatus(snapshot.status)) {
    return { title, body: `${score} · FT` };
  }

  const minute = snapshot.minute > 0 ? ` · ${snapshot.minute}'` : "";
  return { title, body: `${score}${minute}` };
}
