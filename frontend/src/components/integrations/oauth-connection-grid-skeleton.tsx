'use client';

interface SkeletonProps {
  count?: number;
}

export default function OAuthConnectionGridSkeleton({ count = 2 }: SkeletonProps) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="relative flex animate-pulse items-center gap-4 overflow-hidden rounded-2xl border border-border/80 bg-card py-4 pl-5 pr-4"
        >
          <span className="absolute inset-y-0 left-0 w-1 bg-muted" />
          <div className="size-11 shrink-0 rounded-xl bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-3.5 w-40 rounded bg-muted" />
            <div className="h-3 w-56 rounded bg-muted" />
          </div>
          <div className="h-8 w-24 shrink-0 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}
