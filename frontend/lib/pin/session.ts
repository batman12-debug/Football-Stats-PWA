import { fetchLiveMatchStats } from "@/lib/api";
import { isFinishedStatus } from "@/lib/utils";
import type { LiveMatchStats } from "@/types";
import { formatLiveScoreNotification } from "./formatNotification";
import type { PinEntry } from "./types";
import { getActiveEntry } from "./queue";

export const POLL_MS = 10_000;

export interface PinSessionOptions {
  getQueue: () => PinEntry[];
  fetchStats?: (fixtureId: string) => Promise<LiveMatchStats | null>;
  upsertNotification: (input: {
    title: string;
    body: string;
    matchPath: string;
  }) => Promise<"shown" | "denied" | "unsupported">;
  closeNotification: () => void;
  onDequeue: (fixtureId: string) => void;
  now?: () => number;
}

export function createPinSession(options: PinSessionOptions) {
  const fetchStats = options.fetchStats ?? fetchLiveMatchStats;
  let timer: ReturnType<typeof setInterval> | null = null;
  let lastBodyById = new Map<string, string>();

  async function tick() {
    const queue = options.getQueue();
    const active = getActiveEntry(queue);
    if (!active) {
      options.closeNotification();
      return;
    }

    const stats = await fetchStats(active.fixtureId);
    const snapshot = stats
      ? {
          status: stats.status,
          isLive: stats.is_live,
          minute: stats.minute,
          homeGoals: stats.home_goals,
          awayGoals: stats.away_goals,
        }
      : null;

    // Network failure: prefer last known formatted body if we have one for this id
    let title: string;
    let body: string;
    if (!stats && lastBodyById.has(active.fixtureId)) {
      const cached = lastBodyById.get(active.fixtureId)!;
      title = `${(active.homeCode ?? active.homeName.slice(0, 3)).toUpperCase()} vs ${(active.awayCode ?? active.awayName.slice(0, 3)).toUpperCase()}`;
      body = cached;
    } else {
      const formatted = formatLiveScoreNotification(active, snapshot);
      title = formatted.title;
      body = formatted.body;
      if (stats) lastBodyById.set(active.fixtureId, body);
    }

    await options.upsertNotification({
      title,
      body,
      matchPath: `/match/${active.fixtureId}`,
    });

    if (stats && isFinishedStatus(stats.status)) {
      lastBodyById.delete(active.fixtureId);
      options.onDequeue(active.fixtureId);
    }
  }

  return {
    tick,
    start() {
      void tick();
      timer = setInterval(() => {
        void tick();
      }, POLL_MS);
    },
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
    },
  };
}
