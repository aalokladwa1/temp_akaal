import { useEffect, useRef, type FC } from 'react';
import { PrimaryButton } from '../Button';
import styles from './Auth.module.css';

export interface ForgotPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ForgotPasswordModal: FC<ForgotPasswordModalProps> = ({
  isOpen,
  onClose,
}) => {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    // Focus close button on mount
    closeButtonRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className={styles.modalBackdrop}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="forgot-password-modal-title"
    >
      <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
        <header className={styles.modalHeader}>
          <h3 id="forgot-password-modal-title" className={styles.modalTitle}>
            Forgot Password
          </h3>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </header>

        <div className={styles.modalBodyText}>
          <p>Password recovery isn't available yet.</p>
          <p>
            If you're the workspace administrator, password recovery will be
            available from the Administration module in a future release.
          </p>
          <p>
            If you're part of an organization, please contact your system
            administrator.
          </p>
        </div>

        <div className={styles.modalFooter}>
          <PrimaryButton
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            className={styles.modalPrimaryButton}
          >
            Close
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
};
