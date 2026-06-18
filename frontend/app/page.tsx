import { HomeView } from "@/components/HomeView";
import { HeroBlob } from "@/components/HeroBlob";
import { getTeams, getTournamentBracket } from "@/lib/api";

export default async function HomePage() {
  const [bracket, teams] = await Promise.all([getTournamentBracket(), getTeams()]);

  if (!bracket) {
    return (
      <main className="container mx-auto bg-black px-4 py-8 sm:py-10">
        <div className="rounded-xl border border-card-border bg-card p-8 text-center">
          <h1 className="text-2xl font-extrabold">CheckBoard</h1>
          <p className="mt-4 text-muted">
            Tournament data unavailable. The API backend is not reachable from this site.
          </p>
          <p className="mt-3 text-sm text-muted">
            On Netlify, set <code className="text-white/90">API_URL</code> to your hosted
            FastAPI URL (HTTPS), then redeploy. The backend cannot run on localhost.
          </p>
        </div>
      </main>
    );
  }

  return (
    <>
      <HeroBlob />
      <main className="container mx-auto bg-black px-4 pb-8 pt-10 sm:pb-10 sm:pt-16">
        <HomeView bracket={bracket} teamCount={teams.length} />
      </main>
    </>
  );
}
