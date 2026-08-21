import { Outlet } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import MobileHeader from './components/MobileHeader';

export default function App() {
  return (
    <div className="flex min-h-screen bg-surface-50 dark:bg-surface-900">
      <Sidebar />

      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top bar (mobile only — desktop gets the sidebar header) */}
        <header className="lg:hidden h-14 flex items-center px-4
                           bg-white dark:bg-surface-800
                           border-b border-surface-200 dark:border-surface-700">
          <div className="text-sm font-semibold">DeepGuard</div>
          <div className="ml-2 text-xs text-surface-500 dark:text-surface-400">
            AI Image Detector
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 pb-24 lg:pb-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>

        <MobileHeader />
      </div>
    </div>
  );
}
