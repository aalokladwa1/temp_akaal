import type { FC } from 'react';
import type { StepState } from '../../types/wizard';
import styles from './Wizard.module.css';

export interface WizardStepIndicatorProps {
  label: string;
  state: StepState;
}

export const WizardStepIndicator: FC<WizardStepIndicatorProps> = ({ label, state }) => {
  return (
    <div className={styles.navItem} aria-current={state === 'current' ? 'step' : undefined}>
      {state === 'current' ? (
        <span className={styles.indicatorDot} aria-hidden="true" />
      ) : state === 'completed' ? (
        <span className={styles.indicatorCheck} aria-hidden="true">
          ✓
        </span>
      ) : (
        <span className={styles.indicatorCircle} aria-hidden="true" />
      )}

      <span
        className={
          state === 'current'
            ? styles.itemTextCurrent
            : state === 'completed'
            ? styles.itemTextCompleted
            : styles.itemTextUpcoming
        }
      >
        {label}
      </span>
    </div>
  );
};
