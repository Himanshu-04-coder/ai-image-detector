import { NavLink } from 'react-router-dom';
import {
  Upload,
  Files,
  History,
  BarChart3,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { to: '/',        label: 'Analyze',     icon: Upload,   end: true },
  { to: '/batch',   label: 'Batch',       icon: Files },
  { to: '/history', label: 'History',     icon: History },
  { to: '/stats',   label: 'Dashboard',   icon: BarChart3 },
];

export default function Sidebar() {
  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col
                      bg-white dark:bg-surface-800
                      border-r border-surface-200 dark:border-surface-700">
      {/* Brand */}
      <div className="h-16 flex items-center gap-3 px-6 border-b
                      border-surface-200 dark:border-surface-700">
        <div className="w-9 h-9 rounded-lg bg-brand-600 grid place-items-center
                        text-white shadow-sm">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">DeepGuard</div>
          <div className="text-xs text-surface-500 dark:text-surface-400">
            AI Image Detector
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium',
                'transition-colors',
                isActive
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200'
                  : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 '
                  + 'dark:text-surface-300 dark:hover:bg-surface-700/60 '
                  + 'dark:hover:text-white'
              )
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-6 py-4 border-t border-surface-200 dark:border-surface-700
                      text-xs text-surface-500 dark:text-surface-400">
        <div>v0.1.0 — Local</div>
        <div className="mt-1">FastAPI backend @ :8000</div>
      </div>
    </aside>
  );
}
