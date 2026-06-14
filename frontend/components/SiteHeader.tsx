import { Suspense } from "react";

import { GoalMindBrand } from "@/components/GoalMindBrand";
import { HeaderNavLink } from "@/components/HeaderNavLink";
import { MatchesNavMenu } from "@/components/MatchesNavMenu";
import { NavIconSkeleton } from "@/components/NavIcon";

export function SiteHeader() {
  return (
    <header className="site-header sticky top-0 z-50 border-b border-card-border bg-black">
      <div className="container mx-auto flex items-center justify-between gap-3 px-4 py-3 sm:py-4">
        <GoalMindBrand className="min-w-0 shrink" />
        <nav
          className="relative z-50 flex shrink-0 items-center gap-0.5 sm:gap-2"
          aria-label="Main navigation"
        >
          <HeaderNavLink
            href="/"
            exact
            label="Home"
            iconSrc="/icons/nav/home.apng.png"
            staticIconSrc="/icons/nav/home-static.png"
            animatedApng
          />
          <Suspense fallback={<NavIconSkeleton />}>
            <MatchesNavMenu />
          </Suspense>
          <HeaderNavLink href="/teams" label="Teams" iconSrc="/icons/nav/teams.png" />
          <HeaderNavLink href="/news" label="News" iconSrc="/icons/nav/news.png" />
        </nav>
      </div>
    </header>
  );
}
