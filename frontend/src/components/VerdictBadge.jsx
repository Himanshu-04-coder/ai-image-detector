import { CheckCircle2, AlertOctagon } from 'lucide-react';
import { normalizeVerdict, cn, formatPct } from '../lib/utils';

/**
 * Color-coded verdict badge.
 *   REAL  → emerald
 *   AI-GENERATED → red
 * Anything else (UNKNOWN, …) renders neutral.
 */
export default function VerdictBadge({ verdict, confidence, size = 'md' }) {
  const v = normalizeVerdict(verdict);
  const isReal = v === 'REAL';
  const isFake = v === 'AI-GENERATED';

  const palette = isReal
    ? 'bg-ink/10 text-ink ring-ink/30 '
    : isFake
      ? 'bg-marker/10 text-marker ring-marker/30 '
      : 'bg-pencil/10 text-pencil ring-pencil/30 ';

  const sizes = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-sm px-2.5 py-1 gap-1.5',
    lg: 'text-base px-3 py-1.5 gap-2',
  };

  const iconSizes = { sm: 'w-3 h-3', md: 'w-3.5 h-3.5', lg: 'w-4 h-4' };
  const Icon = isReal ? CheckCircle2 : isFake ? AlertOctagon : null;

  return (
    <span
      className={cn(
        'inline-flex items-center wobbly-2 font-semibold border-2',
        palette,
        sizes[size]
      )}
    >
      {Icon ? <Icon className={iconSizes[size]} /> : null}
      <span>{v}</span>
      {confidence !== undefined && confidence !== null && (
        <span className="ml-1 opacity-80 font-medium">
          · {formatPct(confidence)}
        </span>
      )}
    </span>
  );

}
