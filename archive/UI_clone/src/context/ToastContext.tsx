'use client';

import React, { createContext, useContext, useState, useCallback, useEffect, useId } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  variant: ToastVariant;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue>({
  toasts: [],
  addToast: () => {},
  removeToast: () => {},
  success: () => {},
  error: () => {},
  warning: () => {},
  info: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

// ─── Toast Item ───────────────────────────────────────────────────────────────

const VARIANT_CONFIG: Record<ToastVariant, { icon: React.ReactNode; color: string; bg: string; border: string }> = {
  success: {
    color: 'var(--akaal-success)',
    bg: 'var(--akaal-success-bg)',
    border: 'rgba(34,197,94,0.25)',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  error: {
    color: 'var(--akaal-error)',
    bg: 'var(--akaal-error-bg)',
    border: 'rgba(239,68,68,0.25)',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M5 5l6 6M11 5l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
  warning: {
    color: 'var(--akaal-warning)',
    bg: 'var(--akaal-warning-bg)',
    border: 'rgba(250,204,21,0.25)',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M8 3v6M8 11v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
  info: {
    color: 'var(--akaal-info)',
    bg: 'var(--akaal-info-bg)',
    border: 'rgba(96,165,250,0.25)',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M8 7v5M8 5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
};

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: () => void }) {
  const [exiting, setExiting] = useState(false);
  const cfg = VARIANT_CONFIG[toast.variant];

  useEffect(() => {
    const duration = toast.duration ?? 4000;
    const exitTimer = setTimeout(() => setExiting(true), duration - 300);
    const removeTimer = setTimeout(onRemove, duration);
    return () => { clearTimeout(exitTimer); clearTimeout(removeTimer); };
  }, [toast.duration, onRemove]);

  function handleClose() {
    setExiting(true);
    setTimeout(onRemove, 200);
  }

  return (
    <div
      role="alert"
      aria-live="polite"
      className="flex items-start gap-3 p-3.5 rounded-lg min-w-[280px] max-w-[360px]"
      style={{
        background: 'var(--akaal-toast-bg)',
        border: `1px solid var(--akaal-toast-border)`,
        boxShadow: '0 8px 32px var(--akaal-shadow), 0 2px 8px var(--akaal-shadow-sm)',
        animation: exiting
          ? 'toast-slide-out 0.2s ease-in forwards'
          : 'toast-slide-in 0.25s cubic-bezier(0.16,1,0.3,1) forwards',
      }}
    >
      {/* Icon */}
      <div
        className="flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center"
        style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}
      >
        {cfg.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pt-0.5">
        <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
          {toast.title}
        </p>
        {toast.message && (
          <p className="text-xs mt-0.5 leading-relaxed" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
            {toast.message}
          </p>
        )}
      </div>

      {/* Close */}
      <button
        type="button"
        onClick={handleClose}
        aria-label="Dismiss notification"
        className="flex-shrink-0 hover:opacity-70 transition-opacity focus:outline-none focus-visible:ring-1 rounded"
        style={{ color: 'var(--akaal-text-muted)' }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
          <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </button>
    </div>
  );
}

// ─── Toast Container ──────────────────────────────────────────────────────────

function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div
      className="fixed bottom-5 right-5 z-50 flex flex-col gap-2"
      aria-label="Notifications"
      role="region"
    >
      {toasts.map(toast => (
        <ToastItem key={toast.id} toast={toast} onRemove={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts(prev => [...prev, { ...toast, id }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const success = useCallback((title: string, message?: string) => addToast({ variant: 'success', title, message }), [addToast]);
  const error = useCallback((title: string, message?: string) => addToast({ variant: 'error', title, message }), [addToast]);
  const warning = useCallback((title: string, message?: string) => addToast({ variant: 'warning', title, message }), [addToast]);
  const info = useCallback((title: string, message?: string) => addToast({ variant: 'info', title, message }), [addToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, success, error, warning, info }}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
}
