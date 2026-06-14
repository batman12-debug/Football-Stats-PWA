"use client";

import { useId, useMemo } from "react";

import Image from "next/image";

import { isQatarTeam } from "@/lib/isQatarTeam";
import { TEAM_FLAG_GLOW_SVG } from "@/lib/teamFlagGlowSvgContent";
import type { TeamSummary } from "@/types";

interface TeamFlagGlowProps {
  team: Pick<TeamSummary, "name" | "code" | "logo">;
  size?: "sm" | "md" | "lg";
  className?: string;
  priority?: boolean;
}

const SIZE_CLASSES = {
  sm: "h-8 w-8 border",
  md: "h-10 w-10 border sm:h-12 sm:w-12",
  lg: "h-16 w-16 border-2 sm:h-20 sm:w-20",
} as const;

const IMAGE_SIZES = {
  sm: 32,
  md: 48,
  lg: 80,
} as const;

function uniqueGlowSvg(rawId: string): string {
  const suffix = rawId.replace(/:/g, "");
  return TEAM_FLAG_GLOW_SVG.replaceAll("blur1", `blur-${suffix}`);
}

export function TeamFlagGlow({
  team,
  size = "md",
  className = "",
  priority = false,
}: TeamFlagGlowProps) {
  const reactId = useId();
  const glowSvg = useMemo(() => uniqueGlowSvg(reactId), [reactId]);
  const showGlow = isQatarTeam(team);
  const imageSize = IMAGE_SIZES[size];

  return (
    <div
      className={`relative shrink-0 overflow-hidden rounded-full border-card-border bg-black ${SIZE_CLASSES[size]} ${className}`}
    >
      {showGlow && (
        <div
          className="team-flag-glow pointer-events-none absolute inset-0"
          dangerouslySetInnerHTML={{ __html: glowSvg }}
        />
      )}
      {team.logo ? (
        <Image
          src={team.logo}
          alt={`${team.name} flag`}
          width={imageSize}
          height={imageSize}
          className="relative z-10 h-full w-full object-cover"
          priority={priority}
        />
      ) : (
        <span className="relative z-10 flex h-full w-full items-center justify-center text-xs font-bold text-muted sm:text-sm">
          {(team.code ?? team.name.slice(0, 3)).toUpperCase()}
        </span>
      )}
    </div>
  );
}
