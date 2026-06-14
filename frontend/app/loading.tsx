import { MatchGridSkeleton } from "@/components/MatchCardSkeleton";

export default function Loading() {
  return (
    <main className="container mx-auto px-4 py-8 sm:py-10">
      <div className="mb-8">
        <div className="skeleton mb-2 h-9 w-64" />
        <div className="skeleton h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MatchGridSkeleton count={6} />
      </div>
      <p className="sr-only">Loading upcoming matches</p>
    </main>
  );
}
