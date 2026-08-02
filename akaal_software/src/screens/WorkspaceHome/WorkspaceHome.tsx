import type { FC } from 'react';
import type { WorkspaceConfig } from '../../types/workspace';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import styles from './WorkspaceHome.module.css';

export interface WorkspaceHomeProps {
  config: WorkspaceConfig;
}

export const WorkspaceHome: FC<WorkspaceHomeProps> = ({ config }) => {
  return (
    <div className={`enterprise-light-theme ${styles.container}`}>
      <img
        src={backgroundImage}
        alt=""
        aria-hidden="true"
        className={styles.bgImage}
      />

      <div className={styles.card}>
        <h1 className={styles.header}>AKAAL Workspace Ready</h1>
        <div className={styles.workspaceName}>{config.workspaceName}</div>
        <div className={styles.workspacePath}>{config.workspacePath || 'Default Storage Path'}</div>
      </div>
    </div>
  );
};
