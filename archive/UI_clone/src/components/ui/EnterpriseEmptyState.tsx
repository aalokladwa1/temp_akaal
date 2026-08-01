'use client';

import React from 'react';
import Link from 'next/link';

interface EnterpriseEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  primaryAction?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  secondaryAction?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
}

export function EnterpriseEmptyState({
  icon,
  title,
  description,
  primaryAction,
  secondaryAction,
}: EnterpriseEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center rounded-lg border border-dashed"
      style={{
        background: 'var(--akaal-surface-elevated, rgba(26, 35, 51, 0.4))',
        borderColor: 'var(--akaal-border, #2A3647)',
      }}
    >
      <div className="w-12 h-12 rounded-full flex items-center justify-center mb-3 flex-shrink-0"
        style={{
          background: 'var(--akaal-hover-bg, rgba(255,255,255,0.04))',
          border: '1px solid var(--akaal-border, #2A3647)',
          color: 'var(--akaal-text-muted, #64748B)',
        }}
      >
        {icon || (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.4" />
            <path d="M10 7v3M10 13v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
        )}
      </div>

      <h3 className="text-sm font-semibold mb-1" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
        {title}
      </h3>
      <p className="text-xs max-w-md leading-relaxed mb-5" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
        {description}
      </p>

      <div className="flex items-center gap-3 flex-wrap justify-center">
        {primaryAction && (
          primaryAction.href ? (
            <Link
              href={primaryAction.href}
              className="px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 shadow-sm"
              style={{ background: 'var(--akaal-primary, #2563EB)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
            >
              {primaryAction.label}
            </Link>
          ) : (
            <button
              type="button"
              onClick={primaryAction.onClick}
              className="px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 shadow-sm"
              style={{ background: 'var(--akaal-primary, #2563EB)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
            >
              {primaryAction.label}
            </button>
          )
        )}

        {secondaryAction && (
          secondaryAction.href ? (
            <Link
              href={secondaryAction.href}
              className="px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150"
              style={{
                background: 'transparent',
                border: '1px solid var(--akaal-border, #2A3647)',
                color: 'var(--akaal-text-muted, #94A3B8)',
                fontFamily: "'Inter', sans-serif",
              }}
            >
              {secondaryAction.label}
            </Link>
          ) : (
            <button
              type="button"
              onClick={secondaryAction.onClick}
              className="px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150"
              style={{
                background: 'transparent',
                border: '1px solid var(--akaal-border, #2A3647)',
                color: 'var(--akaal-text-muted, #94A3B8)',
                fontFamily: "'Inter', sans-serif",
              }}
            >
              {secondaryAction.label}
            </button>
          )
        )}
      </div>
    </div>
  );
}
