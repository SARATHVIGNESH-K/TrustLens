import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ScanEye, Moon, Sun } from 'lucide-react';
import { useTheme } from '../context/ThemeContext.jsx';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/history', label: 'History' },
  { to: '/admin', label: 'Admin' },
];

export default function Navbar() {
  const { theme, toggle } = useTheme();
  const location = useLocation();

  return (
    <header className="sticky top-0 z-40 border-b border-ink-600/70 bg-ink-900/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2.5 focus-ring">
          <ScanEye className="h-5 w-5 text-scanner-500" strokeWidth={1.75} />
          <span className="font-display text-lg tracking-tight text-paper-100">
            TrustLens
          </span>
        </Link>

        <nav className="hidden items-center gap-1 sm:flex">
          {NAV_ITEMS.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`focus-ring rounded-none px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? 'text-paper-100 border-b-2 border-scanner-500'
                    : 'text-muted-400 hover:text-paper-200'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <button
            onClick={toggle}
            aria-label="Toggle color theme"
            className="focus-ring flex h-8 w-8 items-center justify-center border border-ink-600 text-muted-400 hover:text-scanner-500 hover:border-scanner-600 transition-colors"
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4" strokeWidth={1.75} />
            ) : (
              <Moon className="h-4 w-4" strokeWidth={1.75} />
            )}
          </button>
          <Link
            to="/login"
            className="focus-ring hidden border border-ink-600 px-3.5 py-1.5 text-sm text-paper-200 hover:border-scanner-600 hover:text-scanner-400 transition-colors sm:block"
          >
            Sign in
          </Link>
        </div>
      </div>
    </header>
  );
}
