import { fetchLiveMatchStats } from "@/lib/api";
import { isFinishedStatus } from "@/lib/utils";
import type { LiveMatchStats } from "@/types";
import { buildPinNotificationCard } from "./buildNotificationCard";
import { formatLiveScoreNotification } from "./formatNotification";
import type { NotificationShowInput } from "./notifications";
import type { PinEntry } from "./types";
import { getActiveEntry } from "./queue";

export const POLL_MS = 10_000;
export const CHECKBOARD_ICON_PATH = "/icon.png";

export interface PinSessionOptions {
  getQueue: () => PinEntry[];
  fetchStats?: (fixtureId: string) => Promise<LiveMatchStats | null>;
  upsertNotification: (input: NotificationShowInput) => Promise<"shown" | "denied" | "unsupported">;
  closeNotification: () => void;
  onDequeue: (fixtureId: string) => void;
  buildCard?: typeof buildPinNotificationCard;
  now?: () => number;
}

export function createPinSession(options: PinSessionOptions) {
  const fetchStats = options.fetchStats ?? fetchLiveMatchStats;
  const buildCard = options.buildCard ?? buildPinNotificationCard;
  const now = options.now ?? (() => Date.now());
  let timer: ReturnType<typeof setInterval> | null = null;
  let lastBodyById = new Map<string, string>();
  let lastImageById = new Map<string, string>();

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

    let title: string;
    let body: string;
    if (!stats && lastBodyById.has(active.fixtureId)) {
      const formatted = formatLiveScoreNotification(active, null, now());
      title = formatted.title;
      body = lastBodyById.get(active.fixtureId)!;
    } else {
      const formatted = formatLiveScoreNotification(active, snapshot, now());
      title = formatted.title;
      body = formatted.body;
      if (stats) lastBodyById.set(active.fixtureId, body);
    }

    let image: string | null | undefined = lastImageById.get(active.fixtureId) ?? null;
    if (stats || !image) {
      try {
        image = await buildCard(active, snapshot, now());
        if (image) lastImageById.set(active.fixtureId, image);
      } catch {
        image = lastImageById.get(active.fixtureId) ?? null;
      }
    }

    await options.upsertNotification({
      title,
      body,
      matchPath: `/match/${active.fixtureId}`,
      icon: CHECKBOARD_ICON_PATH,
      image,
    });

    if (stats && isFinishedStatus(stats.status)) {
      lastBodyById.delete(active.fixtureId);
      lastImageById.delete(active.fixtureId);
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
