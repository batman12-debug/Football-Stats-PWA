export function MatchCardSkeleton() {
  return (
    <article className="flex flex-col gap-4 rounded-xl border border-card-border bg-card p-4">
      <div className="skeleton mx-auto h-3 w-32" />
      <div className="match-card-teams">
        <div className="match-card-teams__row">
          <div className="flex justify-center">
            <div className="skeleton h-12 w-12 rounded-full" />
          </div>
          <div className="skeleton h-3 w-6" />
          <div className="flex justify-center">
            <div className="skeleton h-12 w-12 rounded-full" />
          </div>
        </div>
        <div className="match-card-teams__row match-card-teams__names">
          <div className="skeleton mx-auto h-3 w-16" />
          <span aria-hidden="true" />
          <div className="skeleton mx-auto h-3 w-16" />
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
