import type { FC } from 'react';
import styles from './Wizard.module.css';

export interface SetupErrorStateProps {
  message: string;
}

export const SetupErrorState: FC<SetupErrorStateProps> = ({ message }) => {
  return (
    <div className={styles.errorBanner} role="alert">
      <div className={styles.errorBannerTitle}>Persistence Error</div>
      <div className={styles.errorBannerBody}>{message}</div>
    </div>
  );
};
