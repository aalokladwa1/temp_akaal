import type { FC } from 'react';
import { PrimaryButton, SecondaryButton } from '../../components/Button';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import styles from './RecoveryScreen.module.css';

export interface RecoveryScreenProps {
  message?: string | null;
  onAuthenticateAgain: () => void;
  onReconfigureWorkspace: () => void;
}

export const RecoveryScreen: FC<RecoveryScreenProps> = ({
  message,
  onAuthenticateAgain,
  onReconfigureWorkspace,
}) => {
  return (
    <div className={`enterprise-light-theme ${styles.container}`}>
      <img
        src={backgroundImage}
        alt=""
        aria-hidden="true"
        className={styles.bgImage}
      />
      <div className={styles.card}>
        <div className={styles.iconWarning} aria-hidden="true">
          ⚠
        </div>
        <h1 className={styles.title}>Session Could Not Be Restored</h1>
        <p className={styles.bodyText}>
          {message ||
            'Your previous authentication session has expired, been locked, or cannot be restored. Please authenticate again to continue using AKAAL.'}
        </p>

        <div className={styles.buttonRow}>
          <PrimaryButton
            onClick={onAuthenticateAgain}
            className={styles.actionButton}
          >
            Authenticate Again
          </PrimaryButton>
          <SecondaryButton
            onClick={onReconfigureWorkspace}
            className={styles.actionButton}
          >
            Reconfigure Workspace
          </SecondaryButton>
        </div>
      </div>
    </div>
  );
};
