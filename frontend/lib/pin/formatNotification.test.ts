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
