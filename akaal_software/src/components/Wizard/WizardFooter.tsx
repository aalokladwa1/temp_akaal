import type { FC } from 'react';
import type { WizardStepId } from '../../types/wizard';
import { PrimaryButton, SecondaryButton } from '../Button';
import styles from './Wizard.module.css';

export interface WizardFooterProps {
  currentStep: WizardStepId;
  canContinue: boolean;
  isSubmitting?: boolean;
  onBack: () => void;
  onContinue: () => void;
  onFinish: () => void;
}

export const WizardFooter: FC<WizardFooterProps> = ({
  currentStep,
  canContinue,
  isSubmitting = false,
  onBack,
  onContinue,
  onFinish,
}) => {
  const isFirstStep = currentStep === 'workspace';
  const isFinalStep = currentStep === 'review';

  return (
    <div className={styles.footerContainer}>
      <div className={styles.horizontalDivider} />

      <div className={styles.footerButtons}>
        {/* Back button is ALWAYS visible across all steps. Disabled on Step 1. */}
        <SecondaryButton
          type="button"
          onClick={onBack}
          disabled={isFirstStep || isSubmitting}
          className={styles.footerButtonWidth}
        >
          Back
        </SecondaryButton>

        {isFinalStep ? (
          <PrimaryButton
            type="button"
            onClick={onFinish}
            disabled={!canContinue || isSubmitting}
            className={styles.footerButtonWidth}
          >
            {isSubmitting ? 'Saving...' : 'Finish Setup'}
          </PrimaryButton>
        ) : (
          <PrimaryButton
            type="button"
            onClick={onContinue}
            disabled={!canContinue || isSubmitting}
            className={styles.footerButtonWidth}
          >
            Continue
          </PrimaryButton>
        )}
      </div>
    </div>
  );
};
