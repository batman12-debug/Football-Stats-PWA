"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { liveScoreNotifications } from "@/lib/pin/notifications";
import { loadQueue, pinMatch, reorderQueue, saveQueue, unpinMatch } from "@/lib/pin/queue";
import type { PinEntry } from "@/lib/pin/types";

export type PermissionHint = "none" | "denied" | "unsupported";

export interface PinContextValue {
  entries: PinEntry[];
  isPinned: (fixtureId: string) => boolean;
  pin: (entry: PinEntry) => Promise<void>;
  unpin: (fixtureId: string) => void;
  reorder: (fromIndex: number, toIndex: number) => void;
  permissionHint: PermissionHint;
  dismissPermissionHint: () => void;
  sheetOpen: boolean;
  setSheetOpen: (open: boolean) => void;
}

const PinContext = createContext<PinContextValue | null>(null);

export function PinProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<PinEntry[]>([]);
  const [permissionHint, setPermissionHint] = useState<PermissionHint>("none");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // Load the persisted queue once on mount; never touches Notification APIs here.
  useEffect(() => {
    setEntries(loadQueue(window.localStorage));
    setHydrated(true);
  }, []);

  // Skip the first (post-hydration) write so we don't clobber storage with the
  // empty initial state before loadQueue has run.
  useEffect(() => {
    if (!hydrated) return;
    saveQueue(window.localStorage, entries);
  }, [entries, hydrated]);

  const isPinned = useCallback(
    (fixtureId: string) => entries.some((e) => e.fixtureId === fixtureId),
    [entries]
  );

  const pin = useCallback(async (entry: PinEntry) => {
    setEntries((prev) => pinMatch(prev, entry));

    const permission = liveScoreNotifications.getPermission();
    if (permission === "unsupported") {
      setPermissionHint("unsupported");
      return;
    }
    if (permission === "denied") {
      setPermissionHint("denied");
      return;
    }
    if (permission === "default") {
      const result = await liveScoreNotifications.requestPermission();
      if (result === "denied" || result === "unsupported") {
        setPermissionHint(result);
      }
    }
  }, []);

  const unpin = useCallback((fixtureId: string) => {
    setEntries((prev) => unpinMatch(prev, fixtureId));
  }, []);

  const reorder = useCallback((fromIndex: number, toIndex: number) => {
    setEntries((prev) => reorderQueue(prev, fromIndex, toIndex));
  }, []);

  const dismissPermissionHint = useCallback(() => {
    setPermissionHint("none");
  }, []);

  const value = useMemo<PinContextValue>(
    () => ({
      entries,
      isPinned,
      pin,
      unpin,
      reorder,
      permissionHint,
      dismissPermissionHint,
      sheetOpen,
      setSheetOpen,
    }),
    [entries, isPinned, pin, unpin, reorder, permissionHint, dismissPermissionHint, sheetOpen]
  );

  return <PinContext.Provider value={value}>{children}</PinContext.Provider>;
}

export function usePinQueue(): PinContextValue {
  const ctx = useContext(PinContext);
  if (!ctx) {
    throw new Error("usePinQueue must be used within a PinProvider");
  }
  return ctx;
}
