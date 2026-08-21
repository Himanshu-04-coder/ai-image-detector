import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import './index.css';
import App from './App.jsx';
import HomePage from './pages/HomePage.jsx';
import BatchPage from './pages/BatchPage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import StatsPage from './pages/StatsPage.jsx';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'batch',   element: <BatchPage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'stats',   element: <StatsPage /> },
      // Fallback to home for unknown routes.
      { path: '*', element: <HomePage /> },
    ],
  },
]);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} />
    {/* App-wide toast notifications. Theme-aware so it works in dark mode too. */}
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          borderRadius: '10px',
          background: '#1e293b',
          color: '#f8fafc',
          fontSize: '14px',
          maxWidth: '420px',
        },
        success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
        error:   { iconTheme: { primary: '#ef4444', secondary: '#fff' } },
      }}
    />
  </StrictMode>
);
