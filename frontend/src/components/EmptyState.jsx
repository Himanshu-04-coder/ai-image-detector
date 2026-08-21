import { cn } from '../lib/utils';

/**
 * Friendly empty-state block. Used wherever a list/page has nothing to show.
 *
 * Props:
 *   - icon: Lucide icon component
 *   - title: short headline
 *   - description: longer helper text
 *   - action: optional React node for a CTA button/link
 */
export default function EmptyState({
  icon: Icon,
  title = 'Nothing here yet',
  description,
  action,
  className,
}) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center text-center px-6 py-12',
      className
    )}>
      {Icon && (
        <div className="w-14 h-14 rounded-2xl grid place-items-center mb-4
                        bg-white dark:bg-surface-800
                        border border-surface-200 dark:border-surface-700
                        text-brand-600 dark:text-brand-300">
          <Icon className="w-7 h-7" />
        </div>
      )}
      <div className="text-base font-semibold text-surface-800 dark:text-surface-100">
        {title}
      </div>
      {description && (
        <p className="mt-1 text-sm text-surface-500 dark:text-surface-400 max-w-md">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
