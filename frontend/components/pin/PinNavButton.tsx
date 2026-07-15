"use client";

import { usePinQueue } from "@/components/pin/PinContext";

export function PinNavButton() {
  const { entries, setSheetOpen } = usePinQueue();
  const count = entries.length;

  return (
    <button
      type="button"
      aria-label="Pinned"
      title="Pinned"
      onClick={() => setSheetOpen(true)}
      className="group relative inline-flex touch-target shrink-0 items-center justify-center rounded-md p-2 text-muted transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-win/50 sm:min-h-9 sm:min-w-9 sm:p-1.5"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z" />
      </svg>
      {count > 0 ? (
        <span
          aria-hidden="true"
          className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-win px-1 text-[10px] font-semibold leading-none text-black"
        >
          {count > 9 ? "9+" : count}
        </span>
      ) : null}
    </button>
  );
}
