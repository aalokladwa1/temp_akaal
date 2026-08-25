import type { FC } from 'react';
import { useSetupWizard } from '../../hooks/useSetupWizard';
import { WizardLayout } from '../../components/Wizard/WizardLayout';
import { WizardNavigation } from '../../components/Wizard/WizardNavigation';
import { WizardFooter } from '../../components/Wizard/WizardFooter';
import { ReviewSummary } from '../../components/Wizard/ReviewSummary';
import { SetupErrorState } from '../../components/Wizard/SetupErrorState';
import { AdministratorStep } from '../../components/Wizard/AdministratorStep';
import { FormField } from '../../components/Form/FormField';
import { TextInput } from '../../components/Form/TextInput';
import { DirectoryPicker } from '../../components/Form/DirectoryPicker';
import { ThemeRadioGroup } from '../../components/Form/ThemeRadioGroup';
import { WorkspaceReadyScreen } from '../WorkspaceReadyScreen';
import type { WorkspaceConfig } from '../../types/workspace';
import styles from '../../components/Wizard/Wizard.module.css';

export interface SetupWizardScreenProps {
  initialConfig?: Partial<WorkspaceConfig>;
  onLaunchWorkspace: (config: WorkspaceConfig) => void;
}

export const SetupWizardScreen: FC<SetupWizardScreenProps> = ({
  initialConfig,
  onLaunchWorkspace,
}) => {
  const {
    currentStep,
    completedSteps,
    formData,
    isSubmitting,
    submitError,
    isReady,
    verifiedConfig,
    isCurrentStepValid,
    workspaceNameError,
    workspacePathError,
    adminFullNameError,
    adminUsernameError,
    adminPasswordError,
    adminConfirmPasswordError,
    setWorkspaceName,
    setWorkspacePath,
    touchStorageLocation,
    setTheme,
    setAdminField,
    touchAdminField,
    pickStorageDirectory,
    goNext,
    goBack,
    finishSetup,
  } = useSetupWizard({ initialConfig });

  // If finish setup succeeded & verified, render Completion Screen
  if (isReady && verifiedConfig) {
    return (
      <WorkspaceReadyScreen
        config={verifiedConfig}
        onLaunch={() => onLaunchWorkspace(verifiedConfig)}
      />
    );
  }

  return (
    <WizardLayout
      sidebar={
        <WizardNavigation
          currentStep={currentStep}
          completedSteps={completedSteps}
        />
      }
    >
      <div className={styles.stepBody}>
        {/* Step 1: Workspace */}
        {currentStep === 'workspace' && (
          <>
            <header className={styles.stepHeader}>
              <h2 className={styles.stepTitle}>Workspace</h2>
              <p className={styles.stepSubtitle}>
                Choose a name for this AKAAL workspace.
              </p>
            </header>

            <FormField
              label="Workspace Name"
              htmlFor="workspace-name-input"
              error={workspaceNameError}
            >
              <TextInput
                id="workspace-name-input"
                value={formData.workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                hasError={Boolean(workspaceNameError)}
                placeholder="Workspace"
                maxLength={100}
                autoFocus
              />
            </FormField>
          </>
        )}

        {/* Step 2: Storage */}
        {currentStep === 'storage' && (
          <>
            <header className={styles.stepHeader}>
              <h2 className={styles.stepTitle}>Storage</h2>
              <p className={styles.stepSubtitle}>
                Choose where AKAAL stores projects, reports, logs, temporary files, and local settings.
              </p>
            </header>

            <FormField
              label="Workspace Location"
              htmlFor="workspace-storage-input"
              error={workspacePathError}
              helperText="Target storage directory on your local machine."
            >
              <DirectoryPicker
                id="workspace-storage-input"
                value={formData.workspacePath}
                onChange={setWorkspacePath}
                onBrowse={pickStorageDirectory}
                onBlur={touchStorageLocation}
                hasError={Boolean(workspacePathError)}
              />
            </FormField>
          </>
        )}

        {/* Step 3: Appearance */}
        {currentStep === 'appearance' && (
          <>
            <header className={styles.stepHeader}>
              <h2 className={styles.stepTitle}>Appearance</h2>
              <p className={styles.stepSubtitle}>
                Choose the theme used after onboarding.
              </p>
            </header>

            <ThemeRadioGroup
              value={formData.theme}
              onChange={setTheme}
            />
          </>
        )}

        {/* Step 4: Administrator Account */}
        {currentStep === 'administrator' && (
          <>
            <header className={styles.stepHeader}>
              <h2 className={styles.stepTitle}>Administrator Account</h2>
              <p className={styles.stepSubtitle}>
                Create the workspace administrator. These credentials are stored securely using Argon2id hashing.
              </p>
            </header>

            <AdministratorStep
              adminFullName={formData.adminFullName}
              adminUsername={formData.adminUsername}
              adminPassword={formData.adminPassword}
              adminConfirmPassword={formData.adminConfirmPassword}
              adminFullNameError={adminFullNameError}
              adminUsernameError={adminUsernameError}
              adminPasswordError={adminPasswordError}
              adminConfirmPasswordError={adminConfirmPasswordError}
              onChange={(field, value) => setAdminField(field, value)}
              onBlur={(field) => touchAdminField(field)}
            />
          </>
        )}

        {/* Step 5: Review */}
        {currentStep === 'review' && (
          <>
            <header className={styles.stepHeader}>
              <h2 className={styles.stepTitle}>Review</h2>
              <p className={styles.stepSubtitle}>
                Verify your configuration before finishing workspace setup.
              </p>
            </header>

            {submitError && <SetupErrorState message={submitError} />}

            <ReviewSummary data={formData} />
          </>
        )}

        {/* Footer Navigation */}
        <WizardFooter
          currentStep={currentStep}
          canContinue={isCurrentStepValid}
          isSubmitting={isSubmitting}
          onBack={goBack}
          onContinue={goNext}
          onFinish={finishSetup}
        />
      </div>
    </WizardLayout>
  );
};
