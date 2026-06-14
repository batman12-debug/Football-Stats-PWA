import { getBlobSceneSvg } from "@/lib/blobSceneSvg";

const TEAMS_BLOB_SVG = getBlobSceneSvg("blob-scene-haikei-2.svg");

interface TeamsHeroBlobProps {
  teamCount: number;
}

export function TeamsHeroBlob({ teamCount }: TeamsHeroBlobProps) {
  return (
    <section className="hero-blob relative w-full overflow-hidden">
      <div
        className="hero-blob__scene pointer-events-none absolute inset-x-0 top-0 h-full min-h-[inherit]"
        dangerouslySetInnerHTML={{ __html: TEAMS_BLOB_SVG }}
      />

      <div className="hero-blob__content container relative z-10 mx-auto flex min-h-[min(68vh,34rem)] flex-col justify-end gap-1 px-4 pb-10 pt-16 sm:gap-2 sm:pb-12 sm:pt-20">
        <p className="hero-blob__item hero-blob__eyebrow text-sm text-win">
          FIFA World Cup 2026
        </p>
        <h1 className="hero-blob__item hero-blob__headline mt-4 sm:mt-5">
          <span className="hero-blob__headline-line">Teams</span>
        </h1>
        <p className="hero-blob__item hero-blob__lede mt-5 max-w-md text-base text-white/80 sm:mt-6 sm:text-lg">
          {teamCount > 0
            ? `${teamCount} nations. Squads, standings, and historical stats for every team at the tournament.`
            : "World Cup 2026 squads. Select a team to view players, standings, and historical stats."}
        </p>
      </div>
    </section>
  );
}
