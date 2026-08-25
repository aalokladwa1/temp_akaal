import type { FC } from 'react';
import type { WizardStepId } from '../../types/wizard';
import { WizardStepIndicator } from './WizardStepIndicator';
import styles from './Wizard.module.css';

export interface StepItem {
  id: WizardStepId;
  label: string;
}

const STEPS: StepItem[] = [
  { id: 'workspace', label: 'Workspace' },
  { id: 'storage', label: 'Storage' },
  { id: 'appearance', label: 'Appearance' },
  { id: 'administrator', label: 'Administrator Account' },
  { id: 'review', label: 'Review' },
];

export interface WizardNavigationProps {
  currentStep: WizardStepId;
  completedSteps: Set<WizardStepId>;
}

export const WizardNavigation: FC<WizardNavigationProps> = ({
  currentStep,
  completedSteps,
}) => {
  return (
    <aside className={styles.sidebar} aria-label="Setup Steps Navigation">
      <h1 className={styles.sidebarTitle}>Workspace Setup</h1>

      <nav className={styles.navList}>
        {STEPS.map((step) => {
          const isCurrent = currentStep === step.id;
          const isCompleted = completedSteps.has(step.id) && !isCurrent;
          const state = isCurrent ? 'current' : isCompleted ? 'completed' : 'upcoming';

          return <WizardStepIndicator key={step.id} label={step.label} state={state} />;
        })}
      </nav>
    </aside>
  );
};
