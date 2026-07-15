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

/** Injectable browser bridge for tests. */
export type NotificationBridge = NotificationDeps;

export function createBrowserNotificationDeps(): NotificationDeps {
  let lastInstance: Notification | null = null;

  return {
    getNotification: () => (typeof Notification === "undefined" ? undefined : Notification),
    getPermission: () => Notification.permission,
    requestPermission: () => Notification.requestPermission(),
    show: ({ title, options }) => {
      lastInstance?.close();
      const n = new Notification(title, options);
      lastInstance = n;
      n.onclick = () => {
        try {
          window.focus();
          const path =
            typeof options.data === "object" && options.data && "url" in options.data
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
      void tag;
      lastInstance?.close();
      lastInstance = null;
    },
  };
}

export function createNotificationController(deps: NotificationDeps) {
  let last: { close: () => void } | null = null;

  return {
    getPermission(): NotificationPermission | "unsupported" {
      if (!deps.getNotification()) return "unsupported";
      return deps.getPermission();
    },

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

export function getNotificationPermission(): NotificationPermission | "unsupported" {
  return liveScoreNotifications.getPermission();
}

export function requestNotificationPermission(): Promise<NotificationPermission | "unsupported"> {
  return liveScoreNotifications.requestPermission();
}

export function upsertLiveScoreNotification(
  input: NotificationShowInput
): Promise<UpsertResult> {
  return liveScoreNotifications.upsert(input);
}

export function closeLiveScoreNotification(): void {
  liveScoreNotifications.close();
}
