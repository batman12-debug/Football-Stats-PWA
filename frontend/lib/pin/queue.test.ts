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
    homeLogo: null,
    awayLogo: null,
    stageLabel: null,
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
