import { NavLink } from 'react-router-dom';
import { Upload, Files, History, BarChart3 } from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { to: '/',        label: 'Analyze',   icon: Upload,   end: true },
  { to: '/batch',   label: 'Batch',     icon: Files },
  { to: '/history', label: 'History',   icon: History },
  { to: '/stats',   label: 'Dashboard', icon: BarChart3 },
];

// Bottom-nav for tablet/mobile (the sidebar is hidden < lg).
export default function MobileHeader() {
  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30
                    bg-white/95 dark:bg-surface-800/95 backdrop-blur
                    border-t border-surface-200 dark:border-surface-700">
      <ul className="grid grid-cols-4">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex flex-col items-center justify-center py-2 text-xs',
                  isActive
                    ? 'text-brand-600 dark:text-brand-300'
                    : 'text-surface-500 dark:text-surface-400'
                )
              }
            >
              <Icon className="w-5 h-5 mb-0.5" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
