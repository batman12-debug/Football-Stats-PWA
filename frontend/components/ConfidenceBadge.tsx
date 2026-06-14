import type { ConfidenceLevel } from "@/types";
import { getConfidenceLabel } from "@/lib/utils";

interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
}

const STYLES: Record<ConfidenceLevel, string> = {
  low: "border-loss/40 bg-loss/10 text-loss",
  medium: "border-draw/40 bg-draw/10 text-draw",
  high: "border-win/40 bg-win/10 text-win",
};

export function ConfidenceBadge({ level }: ConfidenceBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${STYLES[level]}`}
    >
      {getConfidenceLabel(level)} confidence
    </span>
  );
}
