import { TeamsHeroBlob } from "@/components/TeamsHeroBlob";
import { TeamsView } from "@/components/TeamsView";
import { getTeams, getTournamentBracket } from "@/lib/api";

export default async function TeamsPage() {
  const [teams, bracket] = await Promise.all([getTeams(), getTournamentBracket()]);

  return (
    <>
      <TeamsHeroBlob teamCount={teams.length} />

      <main className="container mx-auto bg-black px-4 pb-8 sm:pb-10 pt-12 sm:pt-16">
        {teams.length === 0 ? (
          <div className="rounded-xl border border-card-border bg-card p-8 text-center">
            <p className="font-semibold">Teams unavailable</p>
            <p className="mt-2 text-sm text-muted">
              Ensure the backend is running and try again shortly.
            </p>
          </div>
        ) : (
          <TeamsView teams={teams} bracket={bracket} />
        )}
      </main>
    </>
  );
}
