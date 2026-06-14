import {
  formatMatchMinute,
  formatMatchScore,
  formatStatusLabel,
  hasScoreboard,
  isFinishedStatus,
  isLiveStatus,
} from "@/lib/utils";

interface MatchScoreboardProps {
  homeGoals: number | null;
  awayGoals: number | null;
  status: string;
  size?: "sm" | "lg";
  liveMinute?: number | null;
}

export function MatchScoreboard({
  homeGoals,
  awayGoals,
  status,
  size = "sm",
  liveMinute,
}: MatchScoreboardProps) {
  const showScore = hasScoreboard(homeGoals, awayGoals);
  const isLive = isLiveStatus(status);
  const isFinished = isFinishedStatus(status);
  const scoreClass = size === "lg" ? "type-display text-3xl sm:text-4xl md:text-5xl" : "type-title text-lg";

  return (
    <div className="flex flex-col items-center gap-1">
      {showScore ? (
        <span className={`tabular-nums ${scoreClass}`}>
          {formatMatchScore(homeGoals!, awayGoals!)}
        </span>
      ) : (
        <span className={size === "lg" ? "type-title text-2xl text-muted" : "type-caps text-xs text-muted"}>
          VS
        </span>
      )}
      {(isLive || isFinished) && (
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ${
            isLive
              ? "bg-loss/15 text-loss ring-loss/30"
              : "bg-win/15 text-win ring-win/30"
          }`}
        >
          {isLive && liveMinute != null
            ? formatMatchMinute(liveMinute, status) ?? formatStatusLabel(status)
            : formatStatusLabel(status)}
        </span>
      )}
    </div>
  );
}
