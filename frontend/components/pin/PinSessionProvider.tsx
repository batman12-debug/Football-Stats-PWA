"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { liveScoreNotifications } from "@/lib/pin/notifications";
import { createPinSession } from "@/lib/pin/session";
import { usePinQueue } from "./PinContext";

export function PinSessionProvider({ children }: { children: ReactNode }) {
  const { entries, unpin } = usePinQueue();

  // Latest queue snapshot for the session's poll loop, so the interval
  // doesn't need to restart on every reorder/mutation.
  const entriesRef = useRef(entries);
  entriesRef.current = entries;

  const activeFixtureId = entries[0]?.fixtureId ?? null;
  const queueLength = entries.length;

  useEffect(() => {
    if (queueLength === 0) {
      liveScoreNotifications.close();
      return;
    }

    const session = createPinSession({
      getQueue: () => entriesRef.current,
      upsertNotification: (input) => liveScoreNotifications.upsert(input),
      closeNotification: () => liveScoreNotifications.close(),
      onDequeue: (fixtureId) => unpin(fixtureId),
    });

    session.start();
    return () => {
      session.stop();
    };
    // Restart only when the active (front-of-queue) fixture changes or the
    // queue transitions to/from empty — not on every mutation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeFixtureId, queueLength, unpin]);

  return <>{children}</>;
}
