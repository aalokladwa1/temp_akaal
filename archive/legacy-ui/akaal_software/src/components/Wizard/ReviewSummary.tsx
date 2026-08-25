import type { FC } from 'react';
import type { WizardFormData } from '../../types/wizard';
import styles from './Wizard.module.css';

export interface ReviewSummaryProps {
  data: WizardFormData;
}

export const ReviewSummary: FC<ReviewSummaryProps> = ({ data }) => {
  const themeLabelMap = {
    light: 'Light',
    dark: 'Dark',
    system: 'Follow System',
  };

  return (
    <div className={styles.reviewList}>
      <div className={styles.reviewItem}>
        <div className={styles.reviewLabel}>Workspace</div>
        <div className={styles.reviewValue}>{data.workspaceName}</div>
      </div>

      <div className={styles.reviewItem}>
        <div className={styles.reviewLabel}>Storage</div>
        <div className={styles.reviewValue}>{data.workspacePath || 'Default Storage Path'}</div>
      </div>

      <div className={styles.reviewItem}>
        <div className={styles.reviewLabel}>Appearance</div>
        <div className={styles.reviewValue}>{themeLabelMap[data.theme] || data.theme}</div>
      </div>

      <div className={styles.reviewItem}>
        <div className={styles.reviewLabel}>Administrator</div>
        <div className={styles.reviewValue}>{data.adminFullName.trim() || '—'}</div>
      </div>

      <div className={styles.reviewItem}>
        <div className={styles.reviewLabel}>Username</div>
        <div className={styles.reviewValue}>
          {data.adminUsername.trim().toLowerCase() || '—'}
        </div>
      </div>
    </div>
  );
};
