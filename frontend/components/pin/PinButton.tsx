"use client";

import type { MouseEvent } from "react";
import { usePinQueue } from "@/components/pin/PinContext";

interface PinButtonProps {
  fixtureId: string;
  homeName: string;
  awayName: string;
  homeCode: string | null;
  awayCode: string | null;
  homeLogo?: string | null;
  awayLogo?: string | null;
  stageLabel?: string | null;
  kickoffIso: string;
  className?: string;
}

export function PinButton({
  fixtureId,
  homeName,
  awayName,
  homeCode,
  awayCode,
  homeLogo = null,
  awayLogo = null,
  stageLabel = null,
  kickoffIso,
  className = "",
}: PinButtonProps) {
  const { isPinned, pin, unpin } = usePinQueue();
  const pinned = isPinned(fixtureId);

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();

    if (pinned) {
      unpin(fixtureId);
      return;
    }

    void pin({
      fixtureId,
      homeName,
      awayName,
      homeCode,
      awayCode,
      homeLogo,
      awayLogo,
      stageLabel,
      kickoffIso,
      pinnedAt: Date.now(),
    });
  };

  return (
    <button
      type="button"
      aria-pressed={pinned}
      aria-label={pinned ? "Unpin match" : "Pin live score"}
      onClick={handleClick}
      className={`pin-button touch-target inline-flex shrink-0 items-center justify-center rounded-full transition-[transform,opacity] duration-[160ms] ease-out active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-win/50 motion-reduce:transition-none motion-reduce:active:scale-100 ${
        pinned ? "text-win" : "text-muted"
      } ${className}`}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z" />
      </svg>
    </button>
  );
}
