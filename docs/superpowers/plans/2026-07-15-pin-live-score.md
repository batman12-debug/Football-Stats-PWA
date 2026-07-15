# Pin Live Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 1 CheckBoard pin live score — unlimited on-device pin queue, one quietly updating system notification for the active match, pin UI on match cards/detail — reusing `GET /api/matches/{id}/live-stats` with no new backend score APIs and no PWA install requirement.

**Architecture:** Client-only feature. `localStorage` holds an ordered `PinEntry[]`. A root `PinSessionProvider` polls live-stats for the queue head, drives a single Notification (`tag: checkboard-live-score`), and on FT removes the head and advances. React context exposes pin/unpin/reorder to `PinButton` and `PinQueueSheet`. Phase 2 Dynamic Island is out of scope for this plan.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind, Vitest (new), browser Notification API, existing `fetchLiveMatchStats`.

## Global Constraints

- No PWA install required; do not claim Dynamic Island / Lock Screen support in UI copy.
- Quiet updates only — replace notification content; do not design goal push banners/sounds.
- Reuse `fetchLiveMatchStats` / `/api/matches/{id}/live-stats`; no new backend score endpoints.
- Storage default: `localStorage` key `checkboard.pinQueue.v1`.
- At most one system notification (stable tag `checkboard-live-score`).
- Active match = first queue entry while status is upcoming or live; on FT, show final once then dequeue and advance or close.
- First pin triggers notification permission (never on page load).
- Permission denied: keep queue + in-app pin state; show enable hint; do not crash.
- Poll failure: keep last known notification body; do not unpin.
- Emil craft: pin press `scale(0.97)` ~160ms ease-out; animate only transform/opacity; hover only under `@media (hover: hover) and (pointer: fine)`; respect `prefers-reduced-motion` / `motion-reduce:`.
- Primary QA target: Android Chrome; iOS = best-effort + honest messaging.
- Do not implement Phase 2 native Live Activities in this plan.

## File map

| File | Responsibility |
| --- | --- |
| `frontend/vitest.config.ts` | Vitest + path alias `@/` |
| `frontend/lib/pin/types.ts` | `PinEntry` and shared pin types |
| `frontend/lib/pin/queue.ts` | Pure queue CRUD + persistence helpers (injectable storage) |
| `frontend/lib/pin/formatNotification.ts` | Upcoming / live / FT notification title+body |
| `frontend/lib/pin/notifications.ts` | Permission + show/update/close Notification |
| `frontend/lib/pin/session.ts` | Poll loop, FT advance, ties queue ↔ live-stats ↔ notifications |
| `frontend/components/pin/PinContext.tsx` | React state + actions over queue |
| `frontend/components/pin/PinSessionProvider.tsx` | Mounts session when queue non-empty |
| `frontend/components/pin/PinButton.tsx` | Pin/unpin control |
| `frontend/components/pin/PinQueueSheet.tsx` | Reorder / unpin drawer |
| `frontend/components/pin/PinNavButton.tsx` | Header entry to open sheet |
| `frontend/lib/pin/*.test.ts` | Unit tests |
| Modify: `frontend/package.json` | `test` script + vitest |
| Modify: `frontend/components/MatchCard.tsx` | PinButton (stop link navigation) |
| Modify: `frontend/components/MatchHeader.tsx` | Accept `fixtureId`, render PinButton |
| Modify: `frontend/app/match/[id]/page.tsx` | Pass `fixtureId` into MatchHeader |
| Modify: `frontend/components/SiteHeader.tsx` | Pin queue nav control |
| Modify: `frontend/app/layout.tsx` | Wrap with Pin providers |
| Modify: `frontend/app/globals.css` | Optional pin button press styles if not purely Tailwind |

---

### Task 1: Vitest + pin queue module

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/lib/pin/types.ts`
- Create: `frontend/lib/pin/queue.ts`
- Create: `frontend/lib/pin/queue.test.ts`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces:
  - `PinEntry` type
  - `STORAGE_KEY = "checkboard.pinQueue.v1"`
  - `createMemoryStorage(): Storage`-like
  - `loadQueue(storage): PinEntry[]`
  - `saveQueue(storage, entries): void`
  - `pinMatch(entries, entry): PinEntry[]` — append if new id; no-op if duplicate
  - `unpinMatch(entries, fixtureId): PinEntry[]`
  - `reorderQueue(entries, fromIndex, toIndex): PinEntry[]`
  - `getActiveEntry(entries): PinEntry | null` — first entry or null

- [ ] **Step 1: Install Vitest and add config**

From `frontend/`:

```bash
npm install -D vitest
```

Add to `package.json` scripts:

```json
"test": "vitest run",
"test:watch": "vitest"
```

Create `frontend/vitest.config.ts`:

```ts
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

- [ ] **Step 2: Write failing queue tests**

Create `frontend/lib/pin/queue.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  createMemoryStorage,
  getActiveEntry,
  loadQueue,
  pinMatch,
  reorderQueue,
  saveQueue,
  unpinMatch,
} from "./queue";
import type { PinEntry } from "./types";

function entry(id: string, home = "France"): PinEntry {
  return {
    fixtureId: id,
    homeName: home,
    awayName: "Spain",
    homeCode: "FRA",
    awayCode: "ESP",
    kickoffIso: "2026-07-15T18:00:00Z",
    pinnedAt: 1,
  };
}

describe("pin queue", () => {
  it("persists and loads ordered entries", () => {
    const storage = createMemoryStorage();
    saveQueue(storage, [entry("1"), entry("2")]);
    expect(loadQueue(storage).map((e) => e.fixtureId)).toEqual(["1", "2"]);
  });

  it("pinMatch appends new and no-ops duplicate", () => {
    const a = entry("1");
    const once = pinMatch([], a);
    expect(once).toHaveLength(1);
    expect(pinMatch(once, entry("1", "Other"))).toEqual(once);
  });

  it("unpinMatch removes by id", () => {
    expect(unpinMatch([entry("1"), entry("2")], "1").map((e) => e.fixtureId)).toEqual(["2"]);
  });

  it("reorderQueue moves items", () => {
    const q = [entry("1"), entry("2"), entry("3")];
    expect(reorderQueue(q, 2, 0).map((e) => e.fixtureId)).toEqual(["3", "1", "2"]);
  });

  it("getActiveEntry returns first or null", () => {
    expect(getActiveEntry([])).toBeNull();
    expect(getActiveEntry([entry("9")])?.fixtureId).toBe("9");
  });
});
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd frontend && npm test
```

Expected: FAIL (module / exports missing).

- [ ] **Step 4: Implement types + queue**

`frontend/lib/pin/types.ts`:

```ts
export interface PinEntry {
  fixtureId: string;
  homeName: string;
  awayName: string;
  homeCode: string | null;
  awayCode: string | null;
  kickoffIso: string;
  pinnedAt: number;
}
```

`frontend/lib/pin/queue.ts`:

```ts
import type { PinEntry } from "./types";

export const STORAGE_KEY = "checkboard.pinQueue.v1";

export function createMemoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear() {
      map.clear();
    },
    getItem(key: string) {
      return map.has(key) ? map.get(key)! : null;
    },
    key(index: number) {
      return [...map.keys()][index] ?? null;
    },
    removeItem(key: string) {
      map.delete(key);
    },
    setItem(key: string, value: string) {
      map.set(key, value);
    },
  };
}

function isPinEntry(value: unknown): value is PinEntry {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return typeof v.fixtureId === "string" && typeof v.homeName === "string" && typeof v.awayName === "string";
}

export function loadQueue(storage: Storage): PinEntry[] {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isPinEntry);
  } catch {
    return [];
  }
}

export function saveQueue(storage: Storage, entries: PinEntry[]): void {
  storage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function pinMatch(entries: PinEntry[], entry: PinEntry): PinEntry[] {
  if (entries.some((e) => e.fixtureId === entry.fixtureId)) return entries;
  return [...entries, entry];
}

export function unpinMatch(entries: PinEntry[], fixtureId: string): PinEntry[] {
  return entries.filter((e) => e.fixtureId !== fixtureId);
}

export function reorderQueue(entries: PinEntry[], fromIndex: number, toIndex: number): PinEntry[] {
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= entries.length ||
    toIndex >= entries.length ||
    fromIndex === toIndex
  ) {
    return entries;
  }
  const next = [...entries];
  const [item] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, item);
  return next;
}

export function getActiveEntry(entries: PinEntry[]): PinEntry | null {
  return entries[0] ?? null;
}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd frontend && npm test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/lib/pin/
git commit -m "feat(pin): add vitest and on-device pin queue module"
```

---

### Task 2: Notification copy formatter

**Files:**
- Create: `frontend/lib/pin/formatNotification.ts`
- Create: `frontend/lib/pin/formatNotification.test.ts`

**Interfaces:**
- Consumes: `PinEntry`; live snapshot fields
- Produces:
  - `LiveScoreSnapshot` type
  - `formatLiveScoreNotification(entry, snapshot | null): { title: string; body: string }`

- [ ] **Step 1: Write failing tests**

```ts
import { describe, expect, it } from "vitest";
import { formatLiveScoreNotification } from "./formatNotification";
import type { PinEntry } from "./types";

const entry: PinEntry = {
  fixtureId: "42",
  homeName: "France",
  awayName: "Spain",
  homeCode: "FRA",
  awayCode: "ESP",
  kickoffIso: "2026-07-15T18:00:00Z",
  pinnedAt: 1,
};

describe("formatLiveScoreNotification", () => {
  it("formats upcoming when snapshot missing or NS", () => {
    const upcoming = formatLiveScoreNotification(entry, null);
    expect(upcoming.title).toContain("FRA");
    expect(upcoming.body.toLowerCase()).toContain("upcoming");

    const ns = formatLiveScoreNotification(entry, {
      status: "NS",
      isLive: false,
      minute: 0,
      homeGoals: null,
      awayGoals: null,
    });
    expect(ns.body.toLowerCase()).toContain("upcoming");
  });

  it("formats live score line", () => {
    const live = formatLiveScoreNotification(entry, {
      status: "2H",
      isLive: true,
      minute: 67,
      homeGoals: 1,
      awayGoals: 0,
    });
    expect(live.body).toMatch(/FRA\s+1[–-]0\s+ESP/);
    expect(live.body).toContain("67");
  });

  it("formats FT final", () => {
    const ft = formatLiveScoreNotification(entry, {
      status: "FT",
      isLive: false,
      minute: 90,
      homeGoals: 2,
      awayGoals: 1,
    });
    expect(ft.body.toLowerCase()).toMatch(/ft|full/);
    expect(ft.body).toMatch(/2/);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- lib/pin/formatNotification.test.ts
```

- [ ] **Step 3: Implement formatter**

```ts
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
```

Use en-dash `–` (U+2013) in the score line to match product copy preference for score separators in notifications (UI elsewhere may still use spaced hyphen via `formatMatchScore` — do not change that helper).

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/pin/formatNotification.ts frontend/lib/pin/formatNotification.test.ts
git commit -m "feat(pin): format quiet live-score notification copy"
```

---

### Task 3: Notification controller

**Files:**
- Create: `frontend/lib/pin/notifications.ts`
- Create: `frontend/lib/pin/notifications.test.ts`

**Interfaces:**
- Produces:
  - `NOTIFICATION_TAG = "checkboard-live-score"`
  - `NotificationBridge` injectable deps for tests
  - `getNotificationPermission(): NotificationPermission | "unsupported"`
  - `requestNotificationPermission(): Promise<NotificationPermission | "unsupported">`
  - `upsertLiveScoreNotification(input): Promise<"shown" | "denied" | "unsupported">`
  - `closeLiveScoreNotification(): void`

- [ ] **Step 1: Write failing tests**

```ts
import { describe, expect, it, vi } from "vitest";
import {
  NOTIFICATION_TAG,
  closeLiveScoreNotification,
  createNotificationController,
} from "./notifications";

describe("notification controller", () => {
  it("returns unsupported when Notification missing", async () => {
    const controller = createNotificationController({
      getNotification: () => undefined,
      getPermission: () => "default",
      requestPermission: async () => "granted",
      show: vi.fn(),
      closeByTag: vi.fn(),
    });
    expect(await controller.upsert({ title: "t", body: "b", matchPath: "/match/1" })).toBe(
      "unsupported"
    );
  });

  it("returns denied without showing when permission denied", async () => {
    const show = vi.fn();
    const controller = createNotificationController({
      getNotification: () => function Fake() {} as unknown as typeof Notification,
      getPermission: () => "denied",
      requestPermission: async () => "denied",
      show,
      closeByTag: vi.fn(),
    });
    expect(await controller.upsert({ title: "t", body: "b", matchPath: "/match/1" })).toBe("denied");
    expect(show).not.toHaveBeenCalled();
  });

  it("shows with stable tag when granted", async () => {
    const show = vi.fn();
    const controller = createNotificationController({
      getNotification: () => function Fake() {} as unknown as typeof Notification,
      getPermission: () => "granted",
      requestPermission: async () => "granted",
      show,
      closeByTag: vi.fn(),
    });
    expect(await controller.upsert({ title: "FRA vs ESP", body: "live", matchPath: "/match/42" })).toBe(
      "shown"
    );
    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "FRA vs ESP",
        options: expect.objectContaining({ tag: NOTIFICATION_TAG, renotify: false }),
      })
    );
  });

  it("closeLiveScoreNotification uses tag", () => {
    const closeByTag = vi.fn();
    const controller = createNotificationController({
      getNotification: () => function Fake() {} as unknown as typeof Notification,
      getPermission: () => "granted",
      requestPermission: async () => "granted",
      show: vi.fn(),
      closeByTag,
    });
    controller.close();
    expect(closeByTag).toHaveBeenCalledWith(NOTIFICATION_TAG);
  });
});
```

Note: Adjust Fake Notification typing as needed so TypeScript compiles; keep behavior identical.

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- lib/pin/notifications.test.ts
```

- [ ] **Step 3: Implement controller**

```ts
export const NOTIFICATION_TAG = "checkboard-live-score";

export interface NotificationShowInput {
  title: string;
  body: string;
  matchPath: string;
}

export type UpsertResult = "shown" | "denied" | "unsupported";

export interface NotificationDeps {
  getNotification: () => typeof Notification | undefined;
  getPermission: () => NotificationPermission;
  requestPermission: () => Promise<NotificationPermission>;
  show: (args: { title: string; options: NotificationOptions }) => void;
  closeByTag: (tag: string) => void;
}

export function createBrowserNotificationDeps(): NotificationDeps {
  return {
    getNotification: () => (typeof Notification === "undefined" ? undefined : Notification),
    getPermission: () => Notification.permission,
    requestPermission: () => Notification.requestPermission(),
    show: ({ title, options }) => {
      const n = new Notification(title, options);
      n.onclick = () => {
        try {
          window.focus();
          const path = typeof options.data === "object" && options.data && "url" in options.data
            ? String((options.data as { url: string }).url)
            : "/";
          window.location.assign(path);
        } catch {
          /* ignore */
        }
        n.close();
      };
    },
    closeByTag: (tag: string) => {
      // Best-effort: browsers without getNotifications cannot enumerate; caller may hold last handle.
      void tag;
    },
  };
}

export function createNotificationController(deps: NotificationDeps) {
  let last: { close: () => void } | null = null;

  return {
    async requestPermission(): Promise<NotificationPermission | "unsupported"> {
      if (!deps.getNotification()) return "unsupported";
      if (deps.getPermission() !== "default") return deps.getPermission();
      return deps.requestPermission();
    },

    async upsert(input: NotificationShowInput): Promise<UpsertResult> {
      if (!deps.getNotification()) return "unsupported";
      const permission = deps.getPermission();
      if (permission !== "granted") return "denied";

      last?.close();
      const options: NotificationOptions = {
        body: input.body,
        tag: NOTIFICATION_TAG,
        renotify: false,
        silent: true,
        data: { url: input.matchPath },
      };
      deps.show({ title: input.title, options });
      last = {
        close: () => deps.closeByTag(NOTIFICATION_TAG),
      };
      // Prefer closing prior Notification instance if show wrapper returns one; keep tag contract.
      return "shown";
    },

    close() {
      try {
        last?.close();
      } finally {
        last = null;
        deps.closeByTag(NOTIFICATION_TAG);
      }
    },
  };
}

/** Default singleton for app code — tests use createNotificationController. */
export const liveScoreNotifications = createNotificationController(createBrowserNotificationDeps());
```

**Refine browser `show`:** track the `Notification` instance and call `.close()` on the previous instance before creating a new one so updates replace quietly. Implement `closeByTag` in browser deps as closing that last instance (tag remains the contract for OS coalescing).

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/pin/notifications.ts frontend/lib/pin/notifications.test.ts
git commit -m "feat(pin): add quiet live-score notification controller"
```

---

### Task 4: Pin session poller (FT advance)

**Files:**
- Create: `frontend/lib/pin/session.ts`
- Create: `frontend/lib/pin/session.test.ts`

**Interfaces:**
- Consumes: queue helpers, formatter, notification controller, `fetchLiveMatchStats`-shaped async fn
- Produces:
  - `POLL_MS = 10_000` (match `LiveMatchStatsPanel`)
  - `createPinSession(options): { start(): void; stop(): void; tick(): Promise<void> }`
  - On FT: after showing FT copy, call `onDequeue(fixtureId)` then continue with new head or `close()` notification

- [ ] **Step 1: Write failing session tests**

```ts
import { describe, expect, it, vi } from "vitest";
import { createPinSession } from "./session";
import type { PinEntry } from "./types";

const baseEntry = (id: string): PinEntry => ({
  fixtureId: id,
  homeName: "France",
  awayName: "Spain",
  homeCode: "FRA",
  awayCode: "ESP",
  kickoffIso: "2026-07-15T18:00:00Z",
  pinnedAt: 1,
});

describe("createPinSession", () => {
  it("does nothing when queue empty", async () => {
    const upsert = vi.fn();
    const close = vi.fn();
    const fetchStats = vi.fn();
    const session = createPinSession({
      getQueue: () => [],
      fetchStats,
      upsertNotification: upsert,
      closeNotification: close,
      onDequeue: vi.fn(),
      now: () => 0,
    });
    await session.tick();
    expect(fetchStats).not.toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
  });

  it("upserts live notification for active match", async () => {
    const upsert = vi.fn().mockResolvedValue("shown");
    const session = createPinSession({
      getQueue: () => [baseEntry("42")],
      fetchStats: async () => ({
        status: "2H",
        is_live: true,
        minute: 67,
        home_goals: 1,
        away_goals: 0,
        home_team: "France",
        away_team: "Spain",
        fixture_id: 42,
        home: {} as never,
        away: {} as never,
      }),
      upsertNotification: upsert,
      closeNotification: vi.fn(),
      onDequeue: vi.fn(),
      now: () => 0,
    });
    await session.tick();
    expect(upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        matchPath: "/match/42",
        body: expect.stringContaining("67"),
      })
    );
  });

  it("on FT shows final then dequeues", async () => {
    const onDequeue = vi.fn();
    const upsert = vi.fn().mockResolvedValue("shown");
    const session = createPinSession({
      getQueue: () => [baseEntry("42"), baseEntry("99")],
      fetchStats: async (id) =>
        id === "42"
          ? {
              status: "FT",
              is_live: false,
              minute: 90,
              home_goals: 2,
              away_goals: 1,
              home_team: "France",
              away_team: "Spain",
              fixture_id: 42,
              home: {} as never,
              away: {} as never,
            }
          : null,
      upsertNotification: upsert,
      closeNotification: vi.fn(),
      onDequeue,
      now: () => 0,
    });
    await session.tick();
    expect(upsert).toHaveBeenCalled();
    expect(onDequeue).toHaveBeenCalledWith("42");
  });

  it("keeps last body on fetch failure (no dequeue)", async () => {
    const onDequeue = vi.fn();
    const upsert = vi.fn().mockResolvedValue("shown");
    const session = createPinSession({
      getQueue: () => [baseEntry("42")],
      fetchStats: async () => null,
      upsertNotification: upsert,
      closeNotification: vi.fn(),
      onDequeue,
      now: () => 0,
    });
    // Seed last known via a prior successful tick would be ideal; for null snapshot, still upsert upcoming from entry metadata — must NOT dequeue.
    await session.tick();
    expect(onDequeue).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- lib/pin/session.test.ts
```

- [ ] **Step 3: Implement session**

```ts
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
```

Spec nuance: “show final briefly, then advance.” Dequeue on the same successful FT poll is correct for Phase 1 (next tick picks new head). Do not add artificial `setTimeout` delays.

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/pin/session.ts frontend/lib/pin/session.test.ts
git commit -m "feat(pin): poll live-stats and auto-advance queue on FT"
```

---

### Task 5: React PinContext + session provider

**Files:**
- Create: `frontend/components/pin/PinContext.tsx`
- Create: `frontend/components/pin/PinSessionProvider.tsx`

**Interfaces:**
- Produces hooks:
  - `usePinQueue(): { entries, isPinned(id), pin(entry), unpin(id), reorder(from, to), permissionHint: "none" | "denied" | "unsupported" }`
  - Providers nest: `PinProvider` (state) → `PinSessionProvider` (effects)

- [ ] **Step 1: Implement PinContext**

Client component. On mount, `loadQueue(window.localStorage)`. Every mutation → `saveQueue`. `pin` should:

1. Build/pass `PinEntry`
2. Update state via `pinMatch`
3. If `Notification` supported and permission `default`, call `liveScoreNotifications.requestPermission()` once
4. Set `permissionHint` to `"denied"` / `"unsupported"` when applicable

Expose:

```ts
export interface PinContextValue {
  entries: PinEntry[];
  isPinned: (fixtureId: string) => boolean;
  pin: (entry: PinEntry) => Promise<void>;
  unpin: (fixtureId: string) => void;
  reorder: (fromIndex: number, toIndex: number) => void;
  permissionHint: "none" | "denied" | "unsupported";
  dismissPermissionHint: () => void;
  sheetOpen: boolean;
  setSheetOpen: (open: boolean) => void;
}
```

- [ ] **Step 2: Implement PinSessionProvider**

```tsx
"use client";
// When entries.length > 0, start createPinSession with:
// getQueue: () => entriesRef.current
// upsert/close via liveScoreNotifications
// onDequeue: (id) => unpin(id)
// stop on unmount or empty queue
```

Use a ref for latest entries so the interval does not restart every render unless queue identity of active id changes — restart when `entries[0]?.fixtureId` changes or length hits 0.

- [ ] **Step 3: Manual typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors in new files (project may have pre-existing issues — fix only pin-related).

- [ ] **Step 4: Commit**

```bash
git add frontend/components/pin/PinContext.tsx frontend/components/pin/PinSessionProvider.tsx
git commit -m "feat(pin): add React pin queue context and session provider"
```

---

### Task 6: PinButton UI (Emil craft)

**Files:**
- Create: `frontend/components/pin/PinButton.tsx`
- Modify: `frontend/app/globals.css` (only if a shared `.pin-button` class is cleaner than Tailwind)

**Interfaces:**
- Consumes: `usePinQueue`, `PinEntry` fields from props
- Props: `{ fixtureId, homeName, awayName, homeCode, awayCode, kickoffIso, className? }`

- [ ] **Step 1: Implement PinButton**

```tsx
"use client";

// button type="button"
// aria-pressed={pinned}
// aria-label={pinned ? "Unpin match" : "Pin live score"}
// onClick: (e) => { e.preventDefault(); e.stopPropagation(); pinned ? unpin(id) : pin({...}) }
// classes:
// - muted when off: text-muted
// - on: text-win
// - active:scale-[0.97] transition-[transform,opacity] duration-[160ms] ease-out
// - motion-reduce:transition-none motion-reduce:active:scale-100
// - hover styles only via media query wrapper or Tailwind arbitrary variant if available;
//   otherwise add to globals.css:
//   @media (hover: hover) and (pointer: fine) {
//     .pin-button:hover { opacity: 0.9; }
//   }
// Use a simple pin / thumbtack SVG (inline), no emoji.
```

- [ ] **Step 2: Visual check in Story-less app later (Task 7)** — no unit test required for SVG button.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/pin/PinButton.tsx frontend/app/globals.css
git commit -m "feat(pin): add pressable PinButton control"
```

---

### Task 7: Wire MatchCard + MatchHeader

**Files:**
- Modify: `frontend/components/MatchCard.tsx`
- Modify: `frontend/components/MatchHeader.tsx`
- Modify: `frontend/app/match/[id]/page.tsx`

- [ ] **Step 1: MatchCard**

Inside the article header row (date row), add `PinButton` only when `canNavigate`. Because card is wrapped in `<Link>`, PinButton must `stopPropagation` (already in Task 6).

Pass:

```tsx
<PinButton
  fixtureId={String(match.id)}
  homeName={home_team.name}
  awayName={away_team.name}
  homeCode={home_team.code}
  awayCode={away_team.code}
  kickoffIso={match.date}
/>
```

Layout: keep date centered; place pin as absolute top-right on the card (`absolute right-2 top-2`) so flag alignment is untouched. Add `relative` to the article.

- [ ] **Step 2: MatchHeader**

Add prop `fixtureId: string`. Render `PinButton` top-right of the header (same absolute pattern). MatchHeader can stay a Server Component importing client `PinButton`.

- [ ] **Step 3: Match detail page**

```tsx
<MatchHeader
  fixtureId={params.id}
  homeTeam={match.home_team}
  ...
/>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/MatchCard.tsx frontend/components/MatchHeader.tsx frontend/app/match/[id]/page.tsx
git commit -m "feat(pin): wire pin control on match cards and detail"
```

---

### Task 8: Pin queue sheet + header entry

**Files:**
- Create: `frontend/components/pin/PinQueueSheet.tsx`
- Create: `frontend/components/pin/PinNavButton.tsx`
- Modify: `frontend/components/SiteHeader.tsx`

- [ ] **Step 1: PinQueueSheet**

Client dialog/sheet:

- One job: manage pins (list order, unpin).
- Empty state: short copy — “Pin a match to track its live score.”
- If `permissionHint === "denied"`: one line — “Notifications blocked — scores still queue in the app. Enable notifications in browser settings.”
- If `permissionHint === "unsupported"`: “This browser can’t show live score notifications. Your pin queue still works in the app.”
- Do **not** mention Dynamic Island.
- Reorder: simple “Move up” / “Move down” buttons (no drag library — YAGNI).
- Unpin button per row.
- Close control; `role="dialog"` + `aria-modal="true"` + Escape to close.

- [ ] **Step 2: PinNavButton**

Header control showing pin icon + count badge when `entries.length > 0`. Opens sheet. Label: “Pinned”.

- [ ] **Step 3: SiteHeader**

Add `<PinNavButton />` and render `<PinQueueSheet />` in the header (or next to nav). Keep sticky header uncluttered — icon-only on small screens with `aria-label`.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/pin/PinQueueSheet.tsx frontend/components/pin/PinNavButton.tsx frontend/components/SiteHeader.tsx
git commit -m "feat(pin): add pin queue sheet and header entry"
```

---

### Task 9: Mount providers in root layout

**Files:**
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Wrap body children**

```tsx
import { PinProvider } from "@/components/pin/PinContext";
import { PinSessionProvider } from "@/components/pin/PinSessionProvider";

// body:
<PinProvider>
  <PinSessionProvider>
    <SiteHeader />
    {children}
  </PinSessionProvider>
</PinProvider>
```

Ensure sheet can portal above content (`fixed inset-0 z-[60]`).

- [ ] **Step 2: Run unit tests + lint**

```bash
cd frontend && npm test && npm run lint
```

Expected: tests PASS; lint clean for touched files.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/layout.tsx
git commit -m "feat(pin): mount pin providers in root layout"
```

---

### Task 10: Manual QA checklist (Android Chrome primary)

**Files:**
- Create: `docs/superpowers/plans/2026-07-15-pin-live-score-qa.md` (short checklist only)

- [ ] **Step 1: Write QA doc** listing:

1. Pin / unpin from card and detail; win-green when on.
2. First pin prompts permission; allow path updates notification; deny keeps queue + hint.
3. With granted permission, notification title/body update on live poll (~10s) without noisy renotify.
4. Simulate FT (or wait): deque + next queued match becomes notification; empty queue closes notification.
5. Reorder changes next active after current FT/dequeue.
6. Kill network mid-live: last score retained; pin remains.
7. Tap notification opens `/match/{id}`.
8. iOS Safari note: document observed limits; no Island claims in UI.

- [ ] **Step 2: Commit QA checklist**

```bash
git add docs/superpowers/plans/2026-07-15-pin-live-score-qa.md
git commit -m "docs(pin): add Phase 1 manual QA checklist"
```

- [ ] **Step 3: Smoke locally**

```bash
cd frontend && npm run dev
```

Walk the checklist on a real Chromium-based browser where Notifications work.

---

## Spec coverage (self-review)

| Spec requirement | Task |
| --- | --- |
| Pin on cards + detail | 6–7 |
| Unlimited ordered queue + reorder/unpin sheet | 1, 5, 8 |
| Active = head while NS/live; FT advance | 4 |
| One quiet notification | 3–4 |
| Permission on first pin; deny keeps queue | 5, 8 |
| Reuse live-stats; no new score APIs | 4 |
| No PWA install / no Island claims | Global + 8 |
| Emil press / motion rules | 6 |
| Poll failure retains score | 4 |
| Android primary / iOS honest | 8, 10 |

## Out of scope (explicit)

- Service worker / push subscriptions
- Account sync
- ActivityKit / Dynamic Island
- Drag-and-drop libraries
- Backend changes

---

## Execution handoff

Plan complete. After user approval of this plan file, implement task-by-task using subagent-driven-development (recommended) or executing-plans.
