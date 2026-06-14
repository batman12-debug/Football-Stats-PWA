import Link from "next/link";

import { GoalMindLogo } from "@/components/GoalMindLogo";
import { getBlobSceneSvg } from "@/lib/blobSceneSvg";
import { matchesViewHref, TOMORROW_VIEW } from "@/lib/matches";

const BLOB_SCENE_SVG = getBlobSceneSvg("blob-scene-haikei.svg");

export function HeroBlob() {
  return (
    <section className="hero-blob relative w-full overflow-hidden">
      <div
        className="hero-blob__scene pointer-events-none absolute inset-x-0 top-0 h-full min-h-[inherit]"
        dangerouslySetInnerHTML={{ __html: BLOB_SCENE_SVG }}
      />

      <div className="hero-blob__content container relative z-10 mx-auto flex min-h-[min(62vh,28rem)] flex-col justify-end gap-1 px-4 pb-8 pt-14 sm:min-h-[min(68vh,34rem)] sm:gap-2 sm:pb-12 sm:pt-20">
        <div className="hero-blob__item max-w-xl">
          <GoalMindLogo className="mb-6 h-12 w-auto sm:mb-7 sm:h-14" priority />
        </div>
        <p className="hero-blob__item hero-blob__eyebrow text-sm text-win">
          FIFA World Cup 2026
        </p>
        <h1 className="hero-blob__item hero-blob__headline mt-4 sm:mt-5">
          <span className="hero-blob__headline-line">Predict.</span>
          <span className="hero-blob__headline-line">Follow.</span>
          <span className="hero-blob__headline-line text-win">Win the</span>
          <span className="hero-blob__headline-line text-win">narrative.</span>
        </h1>
        <p className="hero-blob__item hero-blob__lede mt-5 max-w-md text-base text-white/80 sm:mt-6 sm:text-lg">
          Tournament schedules, team analytics, and match predictions for every stage.
        </p>
        <div className="hero-blob__item mt-6 flex flex-col gap-3 sm:mt-10 sm:flex-row sm:flex-wrap">
          <Link
            href={matchesViewHref(TOMORROW_VIEW)}
            className="hero-blob__cta w-full rounded-lg bg-win px-5 py-3 text-center text-sm text-background transition-transform duration-[160ms] ease-out hover:opacity-90 active:scale-[0.97] sm:w-auto sm:py-2.5"
          >
            View matches tomorrow
          </Link>
          <Link
            href="/teams"
            className="hero-blob__cta w-full rounded-lg border border-white/20 bg-black/40 px-5 py-3 text-center text-sm backdrop-blur-sm transition-[transform,border-color,color] duration-[160ms] ease-out hover:border-win/40 hover:text-white active:scale-[0.97] sm:w-auto sm:py-2.5"
          >
            Explore teams
          </Link>
        </div>
      </div>
    </section>
  );
}
