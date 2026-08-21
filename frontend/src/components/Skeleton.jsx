import { cn } from '../lib/utils';

/**
 * Generic shimmer block. Use width/height/rounded to control shape.
 */
export function Skeleton({ className, ...rest }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'animate-pulse bg-surface-200 dark:bg-surface-700',
        'rounded-md',
        className
      )}
      {...rest}
    />
  );
}

/**
 * Skeleton that mirrors the Stats page layout:
 *   - 4 KPI cards
 *   - 1 confusion-matrix card
 *
 * Shown while the initial stats fetch is in flight so the page
 * doesn't feel "empty" the moment you land on it.
 */
export default function StatsSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading stats">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i}
               className="card-padded flex flex-col gap-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>

      <div className="card-padded">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-24" />
        </div>
        <div className="grid grid-cols-[auto_1fr_1fr] gap-y-1">
          <div />
          <Skeleton className="h-3 w-24 mx-auto" />
          <Skeleton className="h-3 w-24 mx-auto" />
          {[0, 1].map((row) => (
            <div key={row} className="contents">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-24 m-1" />
              <Skeleton className="h-24 m-1" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
