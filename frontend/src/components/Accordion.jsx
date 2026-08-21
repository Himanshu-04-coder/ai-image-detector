import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../lib/utils';

/**
 * Lightweight disclosure / accordion. `items` is an array of:
 *   { title, content, defaultOpen? }
 */
export default function Accordion({ items }) {
  const [openIdx, setOpenIdx] = useState(() => {
    const i = items.findIndex((it) => it.defaultOpen);
    return i >= 0 ? i : -1;
  });

  return (
    <div className="card divide-y divide-surface-200 dark:divide-surface-700">
      {items.map((item, idx) => {
        const open = idx === openIdx;
        return (
          <div key={item.title}>
            <button
              type="button"
              onClick={() => setOpenIdx(open ? -1 : idx)}
              className="w-full flex items-center justify-between gap-3 px-5 py-4
                         text-left text-sm font-medium
                         hover:bg-surface-50 dark:hover:bg-surface-800/60 transition"
              aria-expanded={open}
            >
              <span>{item.title}</span>
              <ChevronDown
                className={cn('w-4 h-4 transition-transform',
                             open && 'rotate-180')}
              />
            </button>
            {open && (
              <div className="px-5 pb-5 animate-fade-in">
                {item.content}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
