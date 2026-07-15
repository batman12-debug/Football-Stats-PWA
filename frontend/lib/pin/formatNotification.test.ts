import { describe, expect, it } from "vitest";
import {
  NOTIFICATION_APP_NAME,
  formatKickoffCenterLines,
  formatLiveScoreNotification,
} from "./formatNotification";
import type { PinEntry } from "./types";

const entry: PinEntry = {
  fixtureId: "42",
  homeName: "France",
  awayName: "Spain",
  homeCode: "FRA",
  awayCode: "ESP",
  homeLogo: null,
  awayLogo: null,
  stageLabel: "Semi-finals",
  kickoffIso: "2026-07-15T18:00:00Z",
  pinnedAt: 1,
};

describe("formatLiveScoreNotification", () => {
  it("uses CheckBoard as the notification title", () => {
    const upcoming = formatLiveScoreNotification(entry, null);
    expect(upcoming.title).toBe(NOTIFICATION_APP_NAME);
    expect(upcoming.body).toContain("France");
    expect(upcoming.body).toContain("Spain");
  });

  it("formats upcoming when snapshot missing or NS", () => {
    const upcoming = formatLiveScoreNotification(entry, null);
    expect(upcoming.title).toBe(NOTIFICATION_APP_NAME);

    const ns = formatLiveScoreNotification(entry, {
      status: "NS",
      isLive: false,
      minute: 0,
      homeGoals: null,
      awayGoals: null,
    });
    expect(ns.title).toBe(NOTIFICATION_APP_NAME);
    expect(ns.body).toMatch(/France vs Spain/);
  });

  it("formats live score line under CheckBoard title", () => {
    const live = formatLiveScoreNotification(entry, {
      status: "2H",
      isLive: true,
      minute: 67,
      homeGoals: 1,
      awayGoals: 0,
    });
    expect(live.title).toBe(NOTIFICATION_APP_NAME);
    expect(live.body).toMatch(/France\s+1[–-]0\s+Spain/);
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
    expect(ft.title).toBe(NOTIFICATION_APP_NAME);
    expect(ft.body.toLowerCase()).toMatch(/ft|full/);
    expect(ft.body).toMatch(/2/);
  });
});

describe("formatKickoffCenterLines", () => {
  it("labels tomorrow relative to PKT now", () => {
    // 2026-07-15 12:00 UTC = 17:00 PKT that day
    const now = Date.parse("2026-07-15T12:00:00Z");
    // Kickoff Jul 16 00:00 PKT = Jul 15 19:00 UTC
    const kickoff = "2026-07-15T19:00:00Z";
    expect(formatKickoffCenterLines(kickoff, now)).toEqual({
      primary: "Tomorrow",
      secondary: "12:00 AM",
    });
  });
});
