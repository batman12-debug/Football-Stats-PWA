import { describe, expect, it, vi } from "vitest";
import { createPinSession } from "./session";
import type { PinEntry } from "./types";

const baseEntry = (id: string): PinEntry => ({
  fixtureId: id,
  homeName: "France",
  awayName: "Spain",
  homeCode: "FRA",
  awayCode: "ESP",
  homeLogo: null,
  awayLogo: null,
  stageLabel: "Semi-finals",
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
      buildCard: async () => null,
      now: () => 0,
    });
    await session.tick();
    expect(fetchStats).not.toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
  });

  it("upserts CheckBoard-branded live notification for active match", async () => {
    const upsert = vi.fn().mockResolvedValue("shown");
    const buildCard = vi.fn().mockResolvedValue("data:image/png;base64,abc");
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
      buildCard,
      now: () => 0,
    });
    await session.tick();
    expect(upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "CheckBoard",
        matchPath: "/match/42",
        body: expect.stringContaining("67"),
        icon: "/icon.png",
        image: "data:image/png;base64,abc",
      })
    );
    expect(buildCard).toHaveBeenCalled();
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
      buildCard: async () => null,
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
      buildCard: async () => null,
      now: () => 0,
    });
    await session.tick();
    expect(onDequeue).not.toHaveBeenCalled();
  });
});
