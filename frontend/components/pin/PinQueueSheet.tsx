"use client";

import { useEffect, useRef } from "react";

import { usePinQueue } from "@/components/pin/PinContext";
import { formatMatchDate } from "@/lib/utils";

function teamLabel(code: string | null, name: string): string {
  return code ?? name;
}

export function PinQueueSheet() {
  const { entries, unpin, reorder, permissionHint, dismissPermissionHint, sheetOpen, setSheetOpen } =
    usePinQueue();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!sheetOpen) return;

    closeButtonRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSheetOpen(false);
    };

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [sheetOpen, setSheetOpen]);

  if (!sheetOpen) return null;

  const hintCopy =
    permissionHint === "denied"
      ? "Notifications blocked — scores still queue in the app. Enable notifications in browser settings."
      : permissionHint === "unsupported"
        ? "This browser can’t show live score notifications. Your pin queue still works in the app."
        : null;

  return (
    <div className="fixed inset-0 z-[200] flex items-end justify-center sm:items-center">
      <button
        type="button"
        aria-label="Close pinned matches"
        onClick={() => setSheetOpen(false)}
        className="absolute inset-0 bg-black/70"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pin-queue-title"
        className="relative z-10 flex max-h-[80vh] w-full max-w-md flex-col overflow-hidden rounded-t-2xl border border-card-border bg-[#0a0a0a] shadow-[0_-12px_40px_rgba(0,0,0,0.85)] sm:rounded-2xl sm:shadow-[0_12px_40px_rgba(0,0,0,0.85)]"
      >
        <div className="flex items-center justify-between gap-3 border-b border-card-border px-4 py-3">
          <h2 id="pin-queue-title" className="text-sm font-semibold text-white">
            Pinned matches
          </h2>
          <button
            ref={closeButtonRef}
            type="button"
            aria-label="Close"
            onClick={() => setSheetOpen(false)}
            className="touch-target inline-flex items-center justify-center rounded-full p-2 text-muted transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-win/50"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M6 6l12 12M18 6L6 18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {hintCopy ? (
          <div className="flex items-start justify-between gap-2 border-b border-card-border bg-[#141414] px-4 py-2.5 text-xs text-muted">
            <p className="leading-snug">{hintCopy}</p>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={dismissPermissionHint}
              className="shrink-0 text-muted transition-colors hover:text-white"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M6 6l12 12M18 6L6 18"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        ) : null}

        <div className="flex-1 overflow-y-auto">
          {entries.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-muted">
              Pin a match to track its live score.
            </p>
          ) : (
            <ul className="divide-y divide-card-border">
              {entries.map((entry, index) => (
                <li key={entry.fixtureId} className="flex items-center gap-2 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-white">
                      {teamLabel(entry.homeCode, entry.homeName)} vs{" "}
                      {teamLabel(entry.awayCode, entry.awayName)}
                    </p>
                    <p className="mt-0.5 text-xs text-muted">
                      {formatMatchDate(entry.kickoffIso)}
                    </p>
                  </div>

                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      aria-label="Move up"
                      disabled={index === 0}
                      onClick={() => reorder(index, index - 1)}
                      className="touch-target inline-flex items-center justify-center rounded-full p-2 text-muted transition-colors hover:text-white disabled:opacity-30 disabled:hover:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-win/50"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path
                          d="M12 19V5M5 12l7-7 7 7"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                    <button
                      type="button"
                      aria-label="Move down"
                      disabled={index === entries.length - 1}
                      onClick={() => reorder(index, index + 1)}
                      className="touch-target inline-flex items-center justify-center rounded-full p-2 text-muted transition-colors hover:text-white disabled:opacity-30 disabled:hover:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-win/50"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path
                          d="M12 5v14M5 12l7 7 7-7"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                    <button
                      type="button"
                      aria-label="Unpin match"
                      onClick={() => unpin(entry.fixtureId)}
                      className="touch-target inline-flex items-center justify-center rounded-full p-2 text-loss transition-colors hover:text-loss/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-win/50"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path
                          d="M6 6l12 12M18 6L6 18"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                        />
                      </svg>
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
