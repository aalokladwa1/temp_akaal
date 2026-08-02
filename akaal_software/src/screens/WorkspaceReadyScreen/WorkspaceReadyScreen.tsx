import type { FC } from 'react';
import type { WorkspaceConfig } from '../../types/workspace';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import { PrimaryButton } from '../../components/Button';
import styles from './WorkspaceReadyScreen.module.css';

export interface WorkspaceReadyScreenProps {
  config: WorkspaceConfig;
  onLaunch: () => void;
}

export const WorkspaceReadyScreen: FC<WorkspaceReadyScreenProps> = ({
  config,
  onLaunch,
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
        <h1 className={styles.title}>Your AKAAL Workspace is Ready</h1>
        <p className={styles.bodyText}>
          Your workspace has been successfully configured. You are ready to start using AKAAL.
        </p>

        <div className={styles.summaryBox}>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Workspace</span>
            <span className={styles.summaryValue}>{config?.workspaceName || 'Workspace'}</span>
          </div>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Location</span>
            <span className={styles.summaryValue}>{config?.workspacePath || 'Default Storage Path'}</span>
          </div>
        </div>

        <PrimaryButton onClick={onLaunch} className={styles.launchButton}>
          Launch AKAAL
        </PrimaryButton>
      </div>
    </div>
  );
};


