import Link from "next/link";

export default function NotFound() {
  return (
    <main className="container mx-auto flex min-h-[50vh] flex-col items-center justify-center px-4 py-16 text-center">
      <h1 className="text-2xl font-extrabold">Match not found</h1>
      <p className="mt-2 text-muted">
        This fixture may not exist or the backend returned no data.
      </p>
      <Link
        href="/matches"
        className="mt-6 rounded-lg border border-card-border bg-card px-4 py-2 text-sm font-semibold transition-colors hover:border-win/40"
      >
        Back to matches
      </Link>
    </main>
  );
}
