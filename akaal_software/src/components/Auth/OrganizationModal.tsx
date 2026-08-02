import { useEffect, type FC } from 'react';
import type { AuthProviderInfo } from '../../types/auth';
import styles from './Auth.module.css';

export interface OrganizationModalProps {
  isOpen: boolean;
  providers: AuthProviderInfo[];
  onClose: () => void;
  onSelectProvider: (provider: AuthProviderInfo) => void;
}

export const OrganizationModal: FC<OrganizationModalProps> = ({
  isOpen,
  providers,
  onClose,
  onSelectProvider,
}) => {
  useEffect(() => {
    if (!isOpen) return;

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
      aria-labelledby="org-modal-title"
    >
      <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
        <header className={styles.modalHeader}>
          <h3 id="org-modal-title" className={styles.modalTitle}>
            Organization Sign-In
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

        <div className={styles.providerList}>
          {providers.map((provider) => {
            const isSelectable = provider.isSelectable;
            return (
              <div
                key={provider.id}
                tabIndex={isSelectable ? 0 : -1}
                className={`${styles.providerItem} ${
                  isSelectable
                    ? styles.providerItemSelectable
                    : styles.providerItemDisabled
                }`}
                onClick={() => {
                  if (isSelectable) {
                    onSelectProvider(provider);
                  }
                }}
                onKeyDown={(e) => {
                  if (isSelectable && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    onSelectProvider(provider);
                  }
                }}
              >
                <span>{provider.name}</span>
                {provider.statusBadge ? (
                  <span className={styles.badgeComingSoon}>
                    {provider.statusBadge}
                  </span>
                ) : (
                  isSelectable && (
                    <span style={{ color: 'var(--akaal-color-bg-primary-btn)' }}>
                      ➔
                    </span>
                  )
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
