import { Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';

/** Indeterminate spinner with optional label, used during API calls. */
export default function Spinner({ label = 'Loading…', className }) {
  return (
    <div className={cn('flex items-center gap-3 text-surface-500 '
                     + 'dark:text-surface-400', className)}>
      <Loader2 className="w-5 h-5 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
