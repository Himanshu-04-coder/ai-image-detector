import { cn, formatPct } from '../lib/utils';

/**
 * Single KPI tile used on the dashboard.
 *  - `label`:    small caption above the value
 *  - `value`:    number 0..1, 0..100, or raw (we normalize via formatPct)
 *  - `icon`:     optional Lucide icon component
 *  - `accent`:   'brand' | 'real' | 'fake' | 'pending'
 *  - `hint`:     small subtitle beneath the value
 */
export default function StatCard({
  label,
  value,
  icon: Icon,
  accent = 'brand',
  hint,
}) {
  const accents = {
    brand:   'bg-paper text-ink',
    real:    'bg-paper text-ink',
    fake:    'bg-paper text-marker',
    pending: 'bg-paper text-pencil',
  };

  return (
    <div className="card-padded flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="text-xs font-medium uppercase tracking-wider
                        text-pencil/60">
          {label}
        </div>
        <div className="mt-1 text-3xl font-semibold tracking-tight">
          {formatPct(value)}
        </div>
        {hint && (
          <div className="mt-1 text-xs text-pencil/60">
            {hint}
          </div>
        )}
      </div>
      {Icon && (
        <div className={cn('w-10 h-10 wobbly-4 grid place-items-center shrink-0 border-2 border-pencil',
                           accents[accent])}>
          <Icon className="w-5 h-5" />
        </div>
      )}
    </div>
  );

}
