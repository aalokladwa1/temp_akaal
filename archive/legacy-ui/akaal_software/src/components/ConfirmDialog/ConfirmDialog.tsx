import { useState, useEffect, useRef, useCallback, type FC } from 'react';
import { ModalContainer } from '../ModalContainer';

export type ConfirmSeverity = 'danger' | 'warning' | 'info';

export interface ConfirmInputConfig {
  value: string;
  onChange: (val: string) => void;
  label?: string;
  placeholder?: string;
  maxLength?: number;
  error?: string | null;
  inputRef?: React.RefObject<HTMLInputElement | null>;
}

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  affectedObject?: string;
  message?: string;
  bulletPoints?: string[];
  consequence?: string;
  confirmText?: string;
  cancelText?: string;
  severity?: ConfirmSeverity;
  evidenceDetails?: string;
  inputConfig?: ConfirmInputConfig;
  isConfirmDisabled?: boolean;
  onConfirm: () => Promise<void> | void;
  onClose: () => void;
}

export const ConfirmDialog: FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  affectedObject,
  message,
  bulletPoints,
  consequence,
  confirmText = title,
  cancelText = 'Cancel',
  severity = 'danger',
  evidenceDetails,
  inputConfig,
  isConfirmDisabled = false,
  onConfirm,
  onClose,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isOpen) {
      setIsSubmitting(false);
      const timer = setTimeout(() => {
        if (inputConfig?.inputRef?.current) {
          inputConfig.inputRef.current.focus();
          inputConfig.inputRef.current.select();
        } else if (confirmBtnRef.current) {
          confirmBtnRef.current.focus();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen, inputConfig?.inputRef]);

  const handleConfirm = useCallback(async () => {
    if (isSubmitting || isConfirmDisabled) return;
    try {
      setIsSubmitting(true);
      await onConfirm();
      onClose();
    } catch (err) {
      console.error('Confirmation handler failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  }, [isSubmitting, isConfirmDisabled, onConfirm, onClose]);

  const isDanger = severity === 'danger';
  const isWarning = severity === 'warning';

  const headerColor = isDanger ? '#EF4444' : isWarning ? '#F59E0B' : '#2563EB';
  const headerBg = isDanger
    ? 'rgba(239, 68, 68, 0.1)'
    : isWarning
    ? 'rgba(245, 158, 11, 0.1)'
    : 'rgba(37, 99, 235, 0.1)';

  const confirmBtnBg = isDanger ? '#EF4444' : isWarning ? '#F59E0B' : '#2563EB';
  const isDisabled = isConfirmDisabled || isSubmitting;

  return (
    <ModalContainer
      isOpen={isOpen}
      onClose={onClose}
      lockBackdrop={isDanger}
      maxWidth={500}
      ariaLabelledBy="confirm-dialog-title"
      ariaDescribedBy="confirm-dialog-message"
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          background: 'var(--dash-surface)',
          borderBottom: '1px solid var(--dash-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: headerBg,
              color: headerColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            {isDanger ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3v6M8 12h.01" strokeLinecap="round" />
              </svg>
            ) : isWarning ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 2l6 11H2L8 2zM8 6v3M8 11h.01" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="8" cy="8" r="6" />
                <path d="M8 5v3M8 10h.01" strokeLinecap="round" />
              </svg>
            )}
          </div>
          <h2
            id="confirm-dialog-title"
            style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)', letterSpacing: '-0.01em' }}
          >
            {title}
          </h2>
        </div>
        <button
          onClick={onClose}
          aria-label="Close dialog"
          style={{
            background: 'none',
            border: 'none',
            fontSize: 18,
            color: 'var(--dash-text-secondary)',
            cursor: 'pointer',
            padding: '2px 6px',
            borderRadius: 4,
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>

      {/* Content Body */}
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {affectedObject && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 8,
              background: 'var(--dash-surface)',
              border: '1px solid var(--dash-border)',
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--dash-text-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span style={{ color: 'var(--dash-text-secondary)', fontWeight: 500 }}>Target:</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{affectedObject}</span>
          </div>
        )}

        {message && (
          <p
            id="confirm-dialog-message"
            style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: 0, lineHeight: 1.5 }}
          >
            {message}
          </p>
        )}

        {inputConfig && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {inputConfig.label && (
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)' }}>
                {inputConfig.label}
              </label>
            )}
            <input
              ref={inputConfig.inputRef}
              type="text"
              value={inputConfig.value}
              maxLength={inputConfig.maxLength || 64}
              onChange={(e) => inputConfig.onChange(e.target.value)}
              placeholder={inputConfig.placeholder}
              disabled={isSubmitting}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleConfirm();
                }
              }}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                background: 'var(--dash-surface)',
                border: inputConfig.error ? '1px solid #EF4444' : '1px solid var(--dash-border)',
                color: 'var(--dash-text-primary)',
                fontSize: 13,
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: inputConfig.error ? '#EF4444' : 'var(--dash-text-secondary)' }}>
                {inputConfig.error || 'Name must be unique'}
              </span>
              {inputConfig.maxLength && (
                <span style={{ color: 'var(--dash-text-secondary)' }}>
                  {inputConfig.value.length}/{inputConfig.maxLength}
                </span>
              )}
            </div>
          </div>
        )}

        {bulletPoints && bulletPoints.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 12px', background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', letterSpacing: '0.04em' }}>
              What Happens Next
            </div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--dash-text-secondary)', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {bulletPoints.map((pt, idx) => (
                <li key={idx} style={{ lineHeight: 1.4 }}>{pt}</li>
              ))}
            </ul>
          </div>
        )}

        {consequence && (
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: isDanger ? '#EF4444' : isWarning ? '#F59E0B' : '#10B981',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span>{isDanger ? '⚠️' : 'ℹ️'}</span>
            <span>{consequence}</span>
          </div>
        )}

        {evidenceDetails && (
          <div
            style={{
              padding: 12,
              borderRadius: 8,
              background: 'var(--dash-surface)',
              border: '1px solid var(--dash-border)',
              fontSize: 12,
              color: 'var(--dash-text-secondary)',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {evidenceDetails}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 6 }}>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              background: 'transparent',
              border: '1px solid var(--dash-border)',
              color: 'var(--dash-text-secondary)',
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {cancelText}
          </button>
          <button
            ref={confirmBtnRef}
            type="button"
            data-confirm-btn="true"
            onClick={handleConfirm}
            disabled={isDisabled}
            style={{
              padding: '8px 20px',
              borderRadius: 8,
              background: confirmBtnBg,
              color: '#ffffff',
              border: 'none',
              fontSize: 13,
              fontWeight: 600,
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              opacity: isDisabled ? 0.6 : 1,
            }}
          >
            {isSubmitting ? 'Processing...' : confirmText}
          </button>
        </div>
      </div>
    </ModalContainer>
  );
};
