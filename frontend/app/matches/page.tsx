import { Suspense } from "react";

import { MatchGridSkeleton } from "@/components/MatchCardSkeleton";
import { MatchesBlobBackground } from "@/components/MatchesBlobBackground";
import { MatchesView } from "@/components/MatchesView";
import { getBlobSceneSvg } from "@/lib/blobSceneSvg";
import { getTournamentBracket } from "@/lib/api";

const TOMORROW_BLOB_SVG = getBlobSceneSvg("blob-scene-haikei-3.svg", "tomorrow");
const STAGE_BLOB_SVG = getBlobSceneSvg("blob-scene-haikei-3.svg", "panel");

async function MatchesContent() {
  const bracket = await getTournamentBracket();

  if (!bracket) {
    return (
      <div className="matches-panel relative isolate pt-8 sm:pt-10">
        <MatchesBlobBackground svg={STAGE_BLOB_SVG} variant="panel" />
        <div className="relative z-10 space-y-8">
          <div>
            <h1 className="type-display text-3xl sm:text-4xl">Matches</h1>
            <p className="mt-2 text-sm text-muted sm:text-base">
              Tomorrow&apos;s fixtures by default. Pick a stage below or from the Matches menu.
            </p>
          </div>
          <div className="rounded-xl border border-card-border bg-black/70 p-8 text-center backdrop-blur-[3px]">
            <p className="text-lg font-semibold">Tournament data unavailable</p>
            <p className="mt-2 text-sm text-muted">
              Ensure the backend is running and try again shortly.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <MatchesView
      bracket={bracket}
      tomorrowBlobSvg={TOMORROW_BLOB_SVG}
      stageBlobSvg={STAGE_BLOB_SVG}
    />
  );
}

export default function MatchesPage() {
  return (
    <main className="container mx-auto bg-black px-4 pb-8 pt-0 sm:pb-10">
      <Suspense
        fallback={
          <div className="space-y-8 pt-8 sm:pt-10">
            <div>
              <h1 className="type-display text-3xl sm:text-4xl">Matches</h1>
              <p className="mt-2 text-sm text-muted sm:text-base">
                Tomorrow&apos;s fixtures by default. Pick a stage below or from the Matches menu.
              </p>
            </div>
            <div className="space-y-6">
              <div className="skeleton h-10 w-full max-w-xs rounded-lg" />
              <MatchGridSkeleton count={6} />
            </div>
          </div>
        }
      >
        <MatchesContent />
      </Suspense>
    </main>
  );
}
