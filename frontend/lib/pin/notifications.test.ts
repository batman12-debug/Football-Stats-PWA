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
