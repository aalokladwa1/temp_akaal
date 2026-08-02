import { useMemo, type FC } from 'react';
import type { WorkspaceConfig } from '../../types/workspace';
import { getEnterpriseGreeting } from '../../utils/greetingUtils';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import styles from './WorkspaceHome.module.css';

export interface WorkspaceHomeProps {
  config: WorkspaceConfig;
}

export const WorkspaceHome: FC<WorkspaceHomeProps> = ({ config }) => {
  const greeting = useMemo(
    () => getEnterpriseGreeting(config.ownerDisplayName),
    [config.ownerDisplayName]
  );

  return (
    <div className={`enterprise-light-theme ${styles.container}`}>
      <img
        src={backgroundImage}
        alt=""
        aria-hidden="true"
        className={styles.bgImage}
      />

      <div className={styles.card}>
        <h1 className={styles.greetingTitle}>{greeting.title}</h1>
        <p className={styles.greetingSubtitle}>{greeting.subtitle}</p>

        <div className={styles.divider} />

        <div className={styles.metaRow}>
          <span className={styles.metaLabel}>Workspace</span>
          <span className={styles.metaValue}>{config.workspaceName}</span>
        </div>
        <div className={styles.metaRow}>
          <span className={styles.metaLabel}>Location</span>
          <span className={styles.metaValue}>{config.workspacePath || 'Default Storage Path'}</span>
        </div>
      </div>
    </div>
  );
};
