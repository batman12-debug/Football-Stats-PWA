import { describe, expect, it, vi } from "vitest";
import {
  NOTIFICATION_TAG,
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
    const closeByTag = vi.fn();
    const controller = createNotificationController({
      getNotification: () => function Fake() {} as unknown as typeof Notification,
      getPermission: () => "granted",
      requestPermission: async () => "granted",
      show,
      closeByTag,
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
    // Updates must not dismiss first — that re-alerts on every poll.
    expect(closeByTag).not.toHaveBeenCalled();
  });

  it("does not re-show when title and body are unchanged", async () => {
    const show = vi.fn();
    const controller = createNotificationController({
      getNotification: () => function Fake() {} as unknown as typeof Notification,
      getPermission: () => "granted",
      requestPermission: async () => "granted",
      show,
      closeByTag: vi.fn(),
    });
    const input = { title: "FRA vs ESP", body: "Upcoming · kickoff", matchPath: "/match/42" };
    expect(await controller.upsert(input)).toBe("shown");
    expect(await controller.upsert(input)).toBe("shown");
    expect(await controller.upsert({ ...input })).toBe("shown");
    expect(show).toHaveBeenCalledTimes(1);
  });

  it("re-shows only when body changes (live update)", async () => {
    const show = vi.fn();
    const controller = createNotificationController({
      getNotification: () => function Fake() {} as unknown as typeof Notification,
      getPermission: () => "granted",
      requestPermission: async () => "granted",
      show,
      closeByTag: vi.fn(),
    });
    await controller.upsert({ title: "FRA vs ESP", body: "FRA 0–0 ESP · 10'", matchPath: "/match/42" });
    await controller.upsert({ title: "FRA vs ESP", body: "FRA 1–0 ESP · 67'", matchPath: "/match/42" });
    expect(show).toHaveBeenCalledTimes(2);
  });

  it("close clears so the next upsert can show again", () => {
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
