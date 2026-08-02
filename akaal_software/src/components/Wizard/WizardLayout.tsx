import type { FC, ReactNode } from 'react';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import styles from './Wizard.module.css';

export interface WizardLayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export const WizardLayout: FC<WizardLayoutProps> = ({ sidebar, children }) => {
  return (
    <div className={`enterprise-light-theme ${styles.wizardWindow}`}>
      <img
        src={backgroundImage}
        alt=""
        aria-hidden="true"
        className={styles.bgImage}
      />

      <div className={styles.surface}>
        {sidebar}
        <div className={styles.verticalDivider} />
        <main className={styles.contentArea}>{children}</main>
      </div>
    </div>
  );
};
