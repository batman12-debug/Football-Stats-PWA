import Link from "next/link";

export default function MatchLoading() {
  return (
    <main className="container mx-auto bg-black px-4 py-8 sm:py-10">
      <Link href="/matches" className="mb-6 inline-flex text-sm text-muted">
        ← Back to matches
      </Link>
      <div className="space-y-6">
        <div className="skeleton h-48 w-full rounded-xl border border-loss/20" />
        <div className="skeleton h-56 w-full rounded-xl" />
        <div className="skeleton h-28 w-full rounded-xl" />
      </div>
      <p className="sr-only">Loading match details</p>
    </main>
  );
}
