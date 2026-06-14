"use client";

import { useEffect, useRef, useState } from "react";

export const NAV_ICON_SIZE = 20;
const APNG_PLAY_MS = 500;

interface NavIconProps {
  src: string;
  /** Static frame shown when the APNG is not playing (Home icon). */
  staticSrc?: string;
  /** Play APNG on hover, then freeze on static frame after 0.5s. */
  animatedApng?: boolean;
  isActive?: boolean;
  /** Driven by the parent Link hover so clicks are never swallowed by img remounts. */
  isHovered?: boolean;
}

export function NavIcon({
  src,
  staticSrc,
  animatedApng = false,
  isActive = false,
  isHovered = false,
}: NavIconProps) {
  const [playKey, setPlayKey] = useState(0);
  const [animating, setAnimating] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const stopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wasHoveredRef = useRef(false);

  const restingSrc = staticSrc ?? src;

  useEffect(() => {
    return () => {
      if (stopTimerRef.current) {
        clearTimeout(stopTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (animatedApng) {
      if (isHovered && !wasHoveredRef.current) {
        if (stopTimerRef.current) {
          clearTimeout(stopTimerRef.current);
        }
        setAnimating(true);
        setPlayKey((key) => key + 1);
        stopTimerRef.current = setTimeout(() => {
          setAnimating(false);
        }, APNG_PLAY_MS);
      } else if (!isHovered) {
        if (stopTimerRef.current) {
          clearTimeout(stopTimerRef.current);
          stopTimerRef.current = null;
        }
        setAnimating(false);
      }
      wasHoveredRef.current = isHovered;
      return;
    }

    if (isHovered && !wasHoveredRef.current) {
      setDrawing(false);
      requestAnimationFrame(() => setDrawing(true));
    } else if (!isHovered) {
      setDrawing(false);
    }
    wasHoveredRef.current = isHovered;
  }, [animatedApng, isHovered]);

  const imgSrc = animatedApng
    ? animating
      ? `${src}?play=${playKey}`
      : restingSrc
    : src;

  return (
    <span
      className={`pointer-events-none relative inline-flex shrink-0 items-center justify-center transition-opacity ${
        isActive ? "opacity-100" : "opacity-60 group-hover:opacity-100"
      }`}
      style={{ width: NAV_ICON_SIZE, height: NAV_ICON_SIZE }}
    >
      <img
        key={animatedApng && animating ? `apng-${playKey}` : "resting"}
        src={imgSrc}
        alt=""
        width={NAV_ICON_SIZE}
        height={NAV_ICON_SIZE}
        draggable={false}
        className={`nav-icon-img pointer-events-none object-contain ${drawing ? "nav-icon-draw" : ""}`}
        style={{ width: NAV_ICON_SIZE, height: NAV_ICON_SIZE }}
        onAnimationEnd={() => setDrawing(false)}
      />
    </span>
  );
}

export function NavIconSkeleton() {
  return (
    <span
      className="inline-block shrink-0 rounded skeleton"
      style={{ width: NAV_ICON_SIZE, height: NAV_ICON_SIZE }}
      aria-hidden="true"
    />
  );
}
