import { useEffect, useRef, type FC, type ReactNode, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';

export interface ModalContainerProps {
  isOpen: boolean;
  onClose: () => void;
  lockBackdrop?: boolean;
  maxWidth?: number;
  ariaLabelledBy?: string;
  ariaDescribedBy?: string;
  children: ReactNode;
}

/**
 * AKAAL Unified Modal Infrastructure
 * Single shared modal shell serving Initialize Migration, Rename, Delete,
 * Archive, Restore, Discard Draft, and all confirmation dialogs.
 * Mounts directly to document.body via React Portal to eliminate container
 * stacking context and scroll isolation issues.
 */
export const ModalContainer: FC<ModalContainerProps> = ({
  isOpen,
  onClose,
  lockBackdrop = false,
  maxWidth = 480,
  ariaLabelledBy,
  ariaDescribedBy,
  children,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  // Single unified scroll-lock implementation for document body & document element
  useEffect(() => {
    if (isOpen) {
      const prevBodyOverflow = document.body.style.overflow;
      const prevDocOverflow = document.documentElement.style.overflow;
      document.body.style.overflow = 'hidden';
      document.documentElement.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prevBodyOverflow;
        document.documentElement.style.overflow = prevDocOverflow;
      };
    }
  }, [isOpen]);

  // Focus restoration to triggering control on close
  useEffect(() => {
    if (isOpen) {
      triggerRef.current = document.activeElement as HTMLElement;
    } else {
      if (triggerRef.current && typeof triggerRef.current.focus === 'function') {
        triggerRef.current.focus();
      }
    }
  }, [isOpen]);

  // Global keydown listener for ESC key
  useEffect(() => {
    if (!isOpen) return;
    const handleGlobalKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [isOpen, onClose]);

  // Focus trap inside modal
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Tab' && modalRef.current) {
      const focusables = modalRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  if (!isOpen) return null;

  const modalNode = (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(11, 15, 23, 0.82)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
      onClick={(e) => {
        if (!lockBackdrop && e.target === e.currentTarget) {
          onClose();
        }
      }}
      onWheel={(e) => {
        if (e.target === e.currentTarget) e.preventDefault();
      }}
      onTouchMove={(e) => {
        if (e.target === e.currentTarget) e.preventDefault();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={ariaLabelledBy}
      aria-describedby={ariaDescribedBy}
      onKeyDown={handleKeyDown}
    >
      <div
        ref={modalRef}
        style={{
          width: '100%',
          maxWidth,
          maxHeight: 'calc(100vh - 48px)',
          overflowY: 'auto',
          background: 'var(--dash-card-bg)',
          border: '1px solid var(--dash-border)',
          borderRadius: 14,
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.35)',
          display: 'flex',
          flexDirection: 'column',
          color: 'var(--dash-text-primary)',
          fontFamily: 'var(--akaal-font-sans, system-ui, sans-serif)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );

  return createPortal(modalNode, document.body);
};
