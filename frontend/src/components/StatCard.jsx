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
    brand:   'bg-brand-50 text-brand-700 '
           + 'dark:bg-brand-900/30 dark:text-brand-300',
    real:    'bg-emerald-50 text-emerald-700 '
           + 'dark:bg-emerald-900/30 dark:text-emerald-300',
    fake:    'bg-red-50 text-red-700 '
           + 'dark:bg-red-900/30 dark:text-red-300',
    pending: 'bg-amber-50 text-amber-700 '
           + 'dark:bg-amber-900/30 dark:text-amber-300',
  };

  return (
    <div className="card-padded flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="text-xs font-medium uppercase tracking-wider
                        text-surface-500 dark:text-surface-400">
          {label}
        </div>
        <div className="mt-1 text-3xl font-semibold tracking-tight">
          {formatPct(value)}
        </div>
        {hint && (
          <div className="mt-1 text-xs text-surface-500 dark:text-surface-400">
            {hint}
          </div>
        )}
      </div>
      {Icon && (
        <div className={cn('w-10 h-10 rounded-lg grid place-items-center shrink-0',
                           accents[accent])}>
          <Icon className="w-5 h-5" />
        </div>
      )}
    </div>
  );
}
