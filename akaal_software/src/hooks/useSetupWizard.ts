import { useState, useCallback, useMemo, useEffect } from 'react';
import type { WizardStepId, WizardFormData } from '../types/wizard';
import type { WorkspaceConfig, ThemePreference } from '../types/workspace';
import { workspaceConfigurationService } from '../services/workspaceConfigurationService';
import { dialogService } from '../services/dialogService';

export interface UseSetupWizardOptions {
  initialConfig?: Partial<WorkspaceConfig>;
  onSetupComplete?: (config: WorkspaceConfig) => void;
}

export function useSetupWizard(options?: UseSetupWizardOptions) {
  const [currentStep, setCurrentStep] = useState<WizardStepId>('workspace');
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStepId>>(new Set());

  const [formData, setFormData] = useState<WizardFormData>({
    workspaceName: options?.initialConfig?.workspaceName || 'Workspace',
    workspacePath: options?.initialConfig?.workspacePath || '',
    theme: options?.initialConfig?.theme || 'light',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [verifiedConfig, setVerifiedConfig] = useState<WorkspaceConfig | null>(null);

  // Field validation computations
  const workspaceNameValidation = useMemo(
    () => workspaceConfigurationService.validateWorkspaceName(formData.workspaceName),
    [formData.workspaceName]
  );

  const [workspacePathError, setWorkspacePathError] = useState<string | undefined>(undefined);
  const [isStorageStepValid, setIsStorageStepValid] = useState<boolean>(false);
  const [isStorageTouched, setIsStorageTouched] = useState<boolean>(false);

  // Live workspace storage path validation effect
  useEffect(() => {
    let isCancelled = false;
    const path = formData.workspacePath;

    workspaceConfigurationService.validateWorkspacePath(path).then((res) => {
      if (isCancelled) return;
      if (res.isValid) {
        setWorkspacePathError(undefined);
        setIsStorageStepValid(true);
      } else {
        setWorkspacePathError(res.error || 'Storage location path is invalid or unwritable.');
        setIsStorageStepValid(false);
      }
    });

    return () => {
      isCancelled = true;
    };
  }, [formData.workspacePath]);

  const touchStorageLocation = useCallback(() => {
    setIsStorageTouched(true);
  }, []);

  const isWorkspaceStepValid = workspaceNameValidation.isValid;
  const isAppearanceStepValid = ['light', 'dark', 'system'].includes(formData.theme);
  const isReviewStepValid = isWorkspaceStepValid && isStorageStepValid && isAppearanceStepValid;

  const isCurrentStepValid = useMemo(() => {
    switch (currentStep) {
      case 'workspace':
        return isWorkspaceStepValid;
      case 'storage':
        return isStorageStepValid;
      case 'appearance':
        return isAppearanceStepValid;
      case 'review':
        return isReviewStepValid;
      default:
        return false;
    }
  }, [currentStep, isWorkspaceStepValid, isStorageStepValid, isAppearanceStepValid, isReviewStepValid]);

  // Actions
  const setWorkspaceName = useCallback((name: string) => {
    setFormData((prev) => ({ ...prev, workspaceName: name }));
    setSubmitError(null);
  }, []);

  const setWorkspacePath = useCallback((path: string) => {
    setFormData((prev) => ({ ...prev, workspacePath: path }));
    setIsStorageTouched(true);
    setSubmitError(null);
  }, []);

  const setTheme = useCallback((theme: ThemePreference) => {
    setFormData((prev) => ({ ...prev, theme }));
    setSubmitError(null);
  }, []);

  const pickStorageDirectory = useCallback(async () => {
    setIsStorageTouched(true);
    try {
      const selected = await dialogService.pickFolder(formData.workspacePath);
      if (selected) {
        setWorkspacePath(selected);
      }
    } catch (err) {
      console.error('Directory selection dialog failed:', err);
    }
  }, [formData.workspacePath, setWorkspacePath]);

  const goNext = useCallback(() => {
    if (!isCurrentStepValid) return;

    setCompletedSteps((prev) => new Set(prev).add(currentStep));

    switch (currentStep) {
      case 'workspace':
        setCurrentStep('storage');
        break;
      case 'storage':
        setCurrentStep('appearance');
        break;
      case 'appearance':
        setCurrentStep('review');
        break;
      case 'review':
        break;
    }
  }, [currentStep, isCurrentStepValid]);

  const goBack = useCallback(() => {
    setSubmitError(null);
    switch (currentStep) {
      case 'workspace':
        // Back is disabled on Step 1
        break;
      case 'storage':
        setCurrentStep('workspace');
        break;
      case 'appearance':
        setCurrentStep('storage');
        break;
      case 'review':
        setCurrentStep('appearance');
        break;
    }
  }, [currentStep]);

  const finishSetup = useCallback(async () => {
    if (!isReviewStepValid || isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const configToSave: WorkspaceConfig = {
        schemaVersion: 1,
        workspaceName: formData.workspaceName.trim(),
        workspacePath: formData.workspacePath.trim(),
        theme: formData.theme,
        onboardingCompleted: true,
      };

      // Configuration Manager handles Save -> Read -> Verify
      const savedConfig = await workspaceConfigurationService.saveAndVerify(configToSave);

      setVerifiedConfig(savedConfig);
      setIsReady(true); // Transition to WorkspaceReadyScreen
      if (options?.onSetupComplete) {
        options.onSetupComplete(savedConfig);
      }
    } catch (err) {
      console.error('Finish setup persistence failed:', err);
      setSubmitError(
        err instanceof Error
          ? err.message
          : 'Failed to create workspace directory or persist workspace configuration. Please verify storage permissions.'
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, isReviewStepValid, isSubmitting, options]);

  return {
    currentStep,
    completedSteps,
    formData,
    isSubmitting,
    submitError,
    isReady,
    verifiedConfig,
    isWorkspaceStepValid,
    isStorageStepValid,
    isAppearanceStepValid,
    isReviewStepValid,
    isCurrentStepValid,
    workspaceNameError: workspaceNameValidation.error,
    workspacePathError: isStorageTouched ? workspacePathError : undefined,
    setWorkspaceName,
    setWorkspacePath,
    touchStorageLocation,
    setTheme,
    pickStorageDirectory,
    goNext,
    goBack,
    finishSetup,
  };
}
