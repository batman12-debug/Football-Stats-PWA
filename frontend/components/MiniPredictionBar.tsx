"use client";

import { useEffect, useState } from "react";

import { formatPercent, stripDisplayDashes } from "@/lib/utils";

interface MiniPredictionBarProps {
  homeWin: number;
  draw: number;
  awayWin: number;
  homeName: string;
  awayName: string;
}

export function MiniPredictionBar({
  homeWin,
  draw,
  awayWin,
  homeName,
  awayName,
}: MiniPredictionBarProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const segment = (value: number) =>
    mounted ? `${value * 100}%` : "0%";

  return (
    <div className="space-y-2">
      <div className="flex h-2 overflow-hidden rounded-full bg-card-border">
        <div
          className="bg-win transition-all duration-700 ease-out motion-reduce:transition-none"
          style={{ width: segment(homeWin) }}
          title={`${stripDisplayDashes(homeName)} win ${formatPercent(homeWin)}`}
        />
        <div
          className="bg-draw transition-all duration-700 ease-out motion-reduce:transition-none"
          style={{ width: segment(draw), transitionDelay: "100ms" }}
          title={`Draw ${formatPercent(draw)}`}
        />
        <div
          className="bg-loss transition-all duration-700 ease-out motion-reduce:transition-none"
          style={{ width: segment(awayWin), transitionDelay: "200ms" }}
          title={`${stripDisplayDashes(awayName)} win ${formatPercent(awayWin)}`}
        />
      </div>
      <div className="flex justify-between text-[10px] font-medium text-muted">
        <span className="text-win">{formatPercent(homeWin)}</span>
        <span className="text-draw">{formatPercent(draw)}</span>
        <span className="text-loss">{formatPercent(awayWin)}</span>
      </div>
    </div>
  );
}
