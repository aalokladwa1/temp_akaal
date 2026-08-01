'use client';

import React, { useState } from 'react';
import { useTheme } from '@/context/ThemeContext';

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);

  const isDark = theme === 'dark';

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex items-center justify-center w-8 h-8 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--akaal-primary)]"
        style={{ color: 'var(--akaal-text-muted)' }}
        aria-label={`Current theme: ${isDark ? 'Midnight Glass (Dark)' : 'Enterprise Blue (Light)'}. Click to switch.`}
        aria-expanded={open}
        onMouseEnter={e => {
          e.currentTarget.style.background = 'var(--akaal-hover-bg)';
          e.currentTarget.style.color = 'var(--akaal-text)';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--akaal-text-muted)';
        }}
      >
        {isDark ? (
          // Moon icon — Midnight Glass
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M13.5 9.5A6 6 0 0 1 6.5 2.5a6 6 0 1 0 7 7Z"
              stroke="currentColor"
              strokeWidth="1.3"
              strokeLinejoin="round"
            />
          </svg>
        ) : (
          // Sun icon — Enterprise Blue
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" />
            <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        )}
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          {/* Dropdown */}
          <div
            className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50"
            style={{
              width: '180px',
              background: 'var(--akaal-surface)',
              border: '1px solid var(--akaal-border)',
              boxShadow: '0 8px 32px var(--akaal-shadow)',
            }}
            role="menu"
            aria-label="Theme selection"
          >
            <div
              className="px-3 py-2"
              style={{ borderBottom: '1px solid var(--akaal-border)' }}
            >
              <p
                className="text-xs font-semibold"
                style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}
              >
                Appearance
              </p>
            </div>

            {/* Enterprise Blue (Light) */}
            <button
              type="button"
              role="menuitem"
              onClick={() => { setTheme('light'); setOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs transition-all duration-150 focus:outline-none"
              style={{
                color: theme === 'light' ? 'var(--akaal-primary)' : 'var(--akaal-text-secondary)',
                fontFamily: "'Inter', sans-serif",
                background: theme === 'light' ? 'var(--akaal-primary-subtle)' : 'transparent',
                borderBottom: '1px solid var(--akaal-border)',
              }}
              onMouseEnter={e => {
                if (theme !== 'light') (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)';
              }}
              onMouseLeave={e => {
                if (theme !== 'light') (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true" style={{ color: theme === 'light' ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)', flexShrink: 0 }}>
                <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" />
                <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
              </svg>
              <div className="text-left">
                <div className="font-medium" style={{ color: theme === 'light' ? 'var(--akaal-primary)' : 'var(--akaal-text)' }}>Enterprise Blue</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontSize: '10px' }}>Light mode</div>
              </div>
              {theme === 'light' && (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="ml-auto flex-shrink-0" style={{ color: 'var(--akaal-primary)' }}>
                  <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>

            {/* Midnight Glass (Dark) */}
            <button
              type="button"
              role="menuitem"
              onClick={() => { setTheme('dark'); setOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs transition-all duration-150 focus:outline-none"
              style={{
                color: theme === 'dark' ? 'var(--akaal-primary)' : 'var(--akaal-text-secondary)',
                fontFamily: "'Inter', sans-serif",
                background: theme === 'dark' ? 'var(--akaal-primary-subtle)' : 'transparent',
              }}
              onMouseEnter={e => {
                if (theme !== 'dark') (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)';
              }}
              onMouseLeave={e => {
                if (theme !== 'dark') (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true" style={{ color: theme === 'dark' ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)', flexShrink: 0 }}>
                <path d="M13.5 9.5A6 6 0 0 1 6.5 2.5a6 6 0 1 0 7 7Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              </svg>
              <div className="text-left">
                <div className="font-medium" style={{ color: theme === 'dark' ? 'var(--akaal-primary)' : 'var(--akaal-text)' }}>Midnight Glass</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontSize: '10px' }}>Dark mode</div>
              </div>
              {theme === 'dark' && (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="ml-auto flex-shrink-0" style={{ color: 'var(--akaal-primary)' }}>
                  <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
