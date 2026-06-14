"use client";

import { useEffect, useState } from "react";

import { formatPercent, stripDisplayDashes } from "@/lib/utils";

interface PredictionBarProps {
  homeWin: number;
  draw: number;
  awayWin: number;
  homeName: string;
  awayName: string;
  label?: string;
}

export function PredictionBar({
  homeWin,
  draw,
  awayWin,
  homeName,
  awayName,
  label = "Win Probability",
}: PredictionBarProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const segment = (value: number) =>
    mounted ? `${value * 100}%` : "0%";

  return (
    <div className="rounded-xl border border-card-border bg-card p-5 sm:p-6">
      <p className="mb-4 text-sm font-medium text-muted">{stripDisplayDashes(label)}</p>

      <div className="flex h-4 overflow-hidden rounded-full bg-card-border sm:h-5">
        <div
          className="bg-win transition-all duration-700 ease-out motion-reduce:transition-none"
          style={{ width: segment(homeWin) }}
        />
        <div
          className="bg-draw transition-all duration-700 ease-out motion-reduce:transition-none"
          style={{ width: segment(draw), transitionDelay: "100ms" }}
        />
        <div
          className="bg-loss transition-all duration-700 ease-out motion-reduce:transition-none"
          style={{ width: segment(awayWin), transitionDelay: "200ms" }}
        />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
        <div>
          <p className="truncate font-semibold text-win">{stripDisplayDashes(homeName)}</p>
          <p className="text-2xl font-extrabold text-win">
            {formatPercent(homeWin)}
          </p>
        </div>
        <div>
          <p className="font-semibold text-draw">Draw</p>
          <p className="text-2xl font-extrabold text-draw">
            {formatPercent(draw)}
          </p>
        </div>
        <div>
          <p className="truncate font-semibold text-loss">{stripDisplayDashes(awayName)}</p>
          <p className="text-2xl font-extrabold text-loss">
            {formatPercent(awayWin)}
          </p>
        </div>
      </div>
    </div>
  );
}
