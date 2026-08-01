'use client';

import React, { useEffect } from 'react';

export type DrawerSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

interface EntityDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  size?: DrawerSize;
  children: React.ReactNode;
  footerActions?: React.ReactNode;
}

export function EntityDrawer({
  isOpen,
  onClose,
  title,
  subtitle,
  badge,
  size = 'md',
  children,
  footerActions,
}: EntityDrawerProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const widthMap: Record<DrawerSize, string> = {
    sm: 'max-w-sm',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-5xl',
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end" aria-modal="true" role="dialog">
      {/* Backdrop */}
      <div
        className="fixed inset-0 transition-opacity"
        style={{ background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(4px)' }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Right-Side Drawer Panel */}
      <div
        className={`relative w-full ${widthMap[size]} flex flex-col h-full shadow-2xl transition-all duration-300 transform translate-x-0`}
        style={{
          background: 'var(--akaal-surface, #141E2E)',
          borderLeft: '1px solid var(--akaal-border, #2A3647)',
          boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Sticky Header */}
        <div
          className="flex items-center justify-between px-6 py-4 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--akaal-border, #2A3647)', background: 'var(--akaal-sidebar-bg, #0D1520)' }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold truncate" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
                  {title}
                </h2>
                {badge}
              </div>
              {subtitle && (
                <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded-md flex items-center justify-center transition-colors focus:outline-none focus-visible:ring-2"
            style={{ color: 'var(--akaal-text-muted, #64748B)' }}
            aria-label="Close drawer"
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg, rgba(255,255,255,0.06))'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text, #F8FAFC)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted, #64748B)'; }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {children}
        </div>

        {/* Sticky Footer Actions */}
        {footerActions && (
          <div
            className="px-6 py-4 flex items-center justify-end gap-3 flex-shrink-0"
            style={{ borderTop: '1px solid var(--akaal-border, #2A3647)', background: 'var(--akaal-sidebar-bg, #0D1520)' }}
          >
            {footerActions}
          </div>
        )}
      </div>
    </div>
  );
}
