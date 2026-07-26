'use client';

import React from 'react';

interface EnterpriseErrorStateProps {
  title: string;
  message: string;
  code?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function EnterpriseErrorState({
  title,
  message,
  code,
  onRetry,
  onDismiss,
}: EnterpriseErrorStateProps) {
  return (
    <div
      className="p-4 rounded-lg border flex items-start gap-3.5 my-3"
      style={{
        background: 'rgba(239, 68, 68, 0.06)',
        borderColor: 'rgba(239, 68, 68, 0.25)',
      }}
    >
      <div
        className="w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444' }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4" />
          <path d="M8 5v4M8 11v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-xs font-semibold" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>
            {title}
          </h4>
          {code && (
            <span className="text-xs px-1.5 py-0.5 rounded font-mono" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444', fontSize: '10px' }}>
              ERR_{code}
            </span>
          )}
        </div>
        <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--akaal-text-muted, #94A3B8)', fontFamily: "'Inter', sans-serif" }}>
          {message}
        </p>

        {(onRetry || onDismiss) && (
          <div className="flex items-center gap-2 mt-3">
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="px-2.5 py-1 rounded text-xs font-medium transition-all duration-150"
                style={{ background: '#EF4444', color: '#fff', fontFamily: "'Inter', sans-serif" }}
              >
                Retry Operation
              </button>
            )}
            {onDismiss && (
              <button
                type="button"
                onClick={onDismiss}
                className="px-2.5 py-1 rounded text-xs font-medium transition-all duration-150"
                style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
              >
                Dismiss
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
