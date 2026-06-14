export function MatchCardSkeleton() {
  return (
    <article className="flex flex-col gap-4 rounded-xl border border-card-border bg-card p-4">
      <div className="skeleton mx-auto h-3 w-32" />
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col items-center gap-2">
          <div className="skeleton h-12 w-12 rounded-full" />
          <div className="skeleton h-3 w-16" />
        </div>
        <div className="skeleton h-3 w-6" />
        <div className="flex flex-col items-center gap-2">
          <div className="skeleton h-12 w-12 rounded-full" />
          <div className="skeleton h-3 w-16" />
        </div>
      </div>
      <div className="skeleton h-2 w-full rounded-full" />
      <div className="flex justify-between">
        <div className="skeleton h-3 w-10" />
        <div className="skeleton h-3 w-10" />
        <div className="skeleton h-3 w-10" />
      </div>
    </article>
  );
}

export function MatchGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <MatchCardSkeleton key={index} />
      ))}
    </>
  );
}
