'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';

export type ToastType = 'success' | 'info' | 'warning' | 'error';

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  type: ToastType;
}

interface ToastContextValue {
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((toast: Omit<ToastMessage, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className="pointer-events-auto rounded-lg p-3.5 shadow-xl transition-all duration-200 border flex items-start gap-3 animate-slide-in"
            style={{
              background: 'var(--akaal-surface, #141E2E)',
              borderColor: t.type === 'success' ? '#22C55E40' : t.type === 'error' ? '#EF444440' : t.type === 'warning' ? '#F59E0B40' : '#38BDF840',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
            }}
          >
            <div
              className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5"
              style={{
                background: t.type === 'success' ? '#22C55E' : t.type === 'error' ? '#EF4444' : t.type === 'warning' ? '#F59E0B' : '#38BDF8',
              }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
                {t.title}
              </p>
              {t.description && (
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
                  {t.description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => setToasts(prev => prev.filter(item => item.id !== t.id))}
              className="text-xs hover:text-white transition-colors"
              style={{ color: 'var(--akaal-text-muted, #64748B)' }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    return {
      addToast: (toast: Omit<ToastMessage, 'id'>) => {
        console.log('[Toast Notice]', toast.title, toast.description);
      },
    };
  }
  return ctx;
}
