'use client';

import React, { useEffect, useRef } from 'react';

export interface ContextMenuItem {
  label: string;
  action: () => void;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
}

interface ContextMenuProps {
  x: number;
  y: number;
  isOpen: boolean;
  onClose: () => void;
  items: ContextMenuItem[];
}

export function ContextMenu({ x, y, isOpen, onClose, items }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={menuRef}
      className="fixed z-50 rounded-lg overflow-hidden shadow-2xl py-1 border"
      style={{
        top: Math.min(y, typeof window !== 'undefined' ? window.innerHeight - 200 : y),
        left: Math.min(x, typeof window !== 'undefined' ? window.innerWidth - 200 : x),
        minWidth: '180px',
        background: 'var(--akaal-surface, #141E2E)',
        borderColor: 'var(--akaal-border, #2A3647)',
        boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
      }}
    >
      {items.map((item, idx) => (
        <button
          key={idx}
          type="button"
          disabled={item.disabled}
          onClick={() => {
            if (!item.disabled) {
              item.action();
              onClose();
            }
          }}
          className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs transition-colors cursor-pointer text-left disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            color: item.danger ? '#EF4444' : 'var(--akaal-text-secondary, #CBD5E1)',
            fontFamily: "'Inter', sans-serif",
          }}
          onMouseEnter={e => {
            if (!item.disabled) {
              (e.currentTarget as HTMLElement).style.background = item.danger ? 'rgba(239, 68, 68, 0.1)' : 'var(--akaal-hover-bg, rgba(255,255,255,0.06))';
            }
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.background = 'transparent';
          }}
        >
          {item.icon && <span className="flex-shrink-0">{item.icon}</span>}
          <span className="flex-1 truncate">{item.label}</span>
        </button>
      ))}
    </div>
  );
}
