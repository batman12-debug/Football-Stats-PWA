import Link from "next/link";

import { CircleScatterBackground } from "@/components/CircleScatterBackground";
import { MatchCard } from "@/components/MatchCard";
import { getCircleScatterSvg } from "@/lib/circleScatterSvg";
import {
  collectAllFixtures,
  filterFixturesForTomorrow,
  formatDayLabel,
  getTomorrowPkt,
  matchesViewHref,
  TOMORROW_VIEW,
} from "@/lib/matches";
import type { BracketFixture, MatchWithPrediction, TournamentBracket } from "@/types";

interface HomeViewProps {
  bracket: TournamentBracket;
  teamCount: number;
}

function toMatchCardProps(fixture: BracketFixture): MatchWithPrediction {
  return { ...fixture, prediction: null };
}

export function HomeView({ bracket, teamCount }: HomeViewProps) {
  const tomorrow = getTomorrowPkt();
  const tomorrowLabel = formatDayLabel(tomorrow);
  const tomorrowFixtures = filterFixturesForTomorrow(collectAllFixtures(bracket), tomorrow);
  const totalMatches = collectAllFixtures(bracket).length;
  const stageCount = bracket.stages.length;
  const circleScatterSvg = getCircleScatterSvg();

  return (
    <div className="home-dashboard relative">
      <CircleScatterBackground svg={circleScatterSvg} />

      <div className="relative z-10 space-y-10 sm:space-y-16">
      {/* World Cup spotlight */}
      <section className="grid items-center gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] lg:gap-12">
        <div className="min-w-0">
          <p className="type-caps text-sm text-win">
            FIFA World Cup 2026
          </p>
          <h2 className="type-display-stack mt-4 text-[clamp(1.75rem,1.25rem+2.5vw,2.75rem)] sm:text-4xl lg:text-[2.75rem]">
            <span className="type-display-stack__line">The Biggest</span>
            <span className="type-display-stack__line">Event in Football</span>
          </h2>
          <p className="type-copy prose-width mt-6 text-sm text-muted sm:text-base">
            {teamCount} nations, {totalMatches} matches, and {stageCount} stages, one trophy
            across the USA, Canada, and Mexico.
          </p>
        </div>

        <div className="relative min-w-0 overflow-hidden rounded-2xl">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/world-cup-celebration.png"
            alt="Argentina celebrate winning the FIFA World Cup, lifting the trophy amid golden fireworks"
            width={1200}
            height={600}
            loading="eager"
            decoding="async"
            className="aspect-[2/1] h-auto w-full object-cover transition-transform duration-300 ease-out motion-reduce:transition-none [@media(hover:hover)]:hover:scale-[1.02]"
          />
        </div>
      </section>

      {/* Next up */}
      <section>
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="type-title text-xl">Next up</h2>
            <p className="type-ui mt-2 text-sm text-muted">{tomorrowLabel} (PKT)</p>
          </div>
          <Link
            href={matchesViewHref(TOMORROW_VIEW)}
            className="text-sm font-medium text-win transition-opacity hover:opacity-80"
          >
            See all matches →
          </Link>
        </div>

        {tomorrowFixtures.length === 0 ? (
          <div className="rounded-xl border border-card-border bg-card p-8 text-center text-sm text-muted">
            No fixtures scheduled for tomorrow. Browse the full tournament schedule.
          </div>
        ) : (
          <div className="match-card-grid">
            {tomorrowFixtures.map((fixture) => (
              <MatchCard key={fixture.id} match={toMatchCardProps(fixture)} />
            ))}
          </div>
        )}
      </section>

      {/* Quick links */}
      <section className="grid gap-4 sm:grid-cols-2">
        <Link
          href={matchesViewHref("group_stage")}
          className="group rounded-xl border border-card-border bg-card p-6 transition-colors hover:border-win/30"
        >
          <h3 className="type-title text-lg group-hover:text-win">Group stage</h3>
          <p className="type-copy mt-3 text-sm text-muted">
            Standings and fixtures for all 12 groups, A through L.
          </p>
        </Link>
        <Link
          href={matchesViewHref("final")}
          className="group rounded-xl border border-card-border bg-card p-6 transition-colors hover:border-win/30"
        >
          <h3 className="type-title text-lg group-hover:text-win">Road to the final</h3>
          <p className="type-copy mt-3 text-sm text-muted">
            Knockout bracket from the Round of 32 through the final.
          </p>
        </Link>
      </section>
      </div>
    </div>
  );
}
