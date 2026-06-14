"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { NavIcon } from "@/components/NavIcon";
import {
  TOMORROW_VIEW,
  TOURNAMENT_STAGES,
  formatDayLabel,
  getTomorrowPkt,
  matchesViewHref,
  parseMatchesView,
} from "@/lib/matches";

export function MatchesNavMenu() {
  const containerRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [canHover, setCanHover] = useState(false);

  const tomorrowLabel = useMemo(() => formatDayLabel(getTomorrowPkt()), []);
  const currentView = parseMatchesView(searchParams.get("view"));
  const isMatchesPage = pathname === "/matches";

  useEffect(() => {
    setCanHover(window.matchMedia("(hover: hover) and (pointer: fine)").matches);
  }, []);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: PointerEvent) => {
      if (containerRef.current?.contains(event.target as Node)) return;
      setOpen(false);
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div
      ref={containerRef}
      className="relative"
      onMouseEnter={() => {
        if (canHover) setOpen(true);
      }}
      onMouseLeave={() => {
        if (canHover) setOpen(false);
      }}
    >
      <button
        type="button"
        aria-label="Matches"
        title="Matches"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onFocus={() => setIsHovered(true)}
        onBlur={() => setIsHovered(false)}
        className={`group inline-flex touch-target cursor-pointer items-center justify-center rounded-md p-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-win/50 sm:min-h-9 sm:min-w-9 sm:p-1.5 ${
          isMatchesPage ? "text-white" : "text-muted hover:text-white"
        }`}
      >
        <NavIcon src="/icons/nav/matches.png" isActive={isMatchesPage} isHovered={isHovered} />
      </button>

      {open ? (
        <div className="absolute right-0 top-full z-[100] min-w-[14rem]">
          {/* Keeps hover active while moving from the icon to the menu */}
          <div className="h-2" aria-hidden="true" />
          <div
            role="menu"
            className="overflow-hidden rounded-lg border border-[#333333] bg-[#141414] py-1 shadow-[0_12px_40px_rgba(0,0,0,0.85)]"
          >
            <Link
              href={matchesViewHref(TOMORROW_VIEW)}
              role="menuitem"
              onClick={() => setOpen(false)}
              className={`block min-h-11 px-4 py-3 text-sm transition-colors hover:bg-[#222222] hover:text-white ${
                isMatchesPage && currentView === TOMORROW_VIEW ? "text-win" : "text-muted"
              }`}
            >
              Tomorrow
              <span className="mt-0.5 block text-xs opacity-70">{tomorrowLabel}</span>
            </Link>

            <div className="my-1 border-t border-[#333333]" />

            {TOURNAMENT_STAGES.map((stage) => (
              <Link
                key={stage.value}
                href={matchesViewHref(stage.value)}
                role="menuitem"
                onClick={() => setOpen(false)}
                className={`block min-h-11 px-4 py-3 text-sm transition-colors hover:bg-[#222222] hover:text-white ${
                  isMatchesPage && currentView === stage.value ? "text-win" : "text-muted"
                }`}
              >
                {stage.label}
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
