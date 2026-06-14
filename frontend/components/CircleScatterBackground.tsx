"use client";

import { useLayoutEffect, useRef } from "react";

interface CircleScatterBackgroundProps {
  svg: string;
}

function revealScatter(root: HTMLDivElement) {
  root.setAttribute("data-visible", "true");
}

function isInViewport(root: HTMLElement): boolean {
  const rect = root.getBoundingClientRect();
  return rect.top < window.innerHeight * 0.92 && rect.bottom > window.innerHeight * 0.08;
}

export function CircleScatterBackground({ svg }: CircleScatterBackgroundProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      revealScatter(root);
      return;
    }

    if (isInViewport(root)) {
      revealScatter(root);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          revealScatter(root);
          observer.disconnect();
        }
      },
      { threshold: 0, rootMargin: "0px 0px -10% 0px" },
    );

    observer.observe(root);

    const onScroll = () => {
      if (isInViewport(root)) {
        revealScatter(root);
        observer.disconnect();
        window.removeEventListener("scroll", onScroll, { capture: true });
      }
    };

    window.addEventListener("scroll", onScroll, { capture: true, passive: true });

    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", onScroll, { capture: true });
    };
  }, []);

  return (
    <div
      ref={rootRef}
      className="circle-scatter pointer-events-none overflow-hidden"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
