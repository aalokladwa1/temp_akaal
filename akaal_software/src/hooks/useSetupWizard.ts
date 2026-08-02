import { useState, useCallback, useMemo, useEffect } from 'react';
import type { WizardStepId, WizardFormData } from '../types/wizard';
import type { WorkspaceConfig, ThemePreference } from '../types/workspace';
import { workspaceConfigurationService } from '../services/workspaceConfigurationService';
import { dialogService } from '../services/dialogService';
import { ipcService } from '../services/ipcService';

export interface UseSetupWizardOptions {
  initialConfig?: Partial<WorkspaceConfig>;
  onSetupComplete?: (config: WorkspaceConfig) => void;
}

// Administrator field validation helpers
function validateAdminFullName(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return 'Full name is required.';
  if (trimmed.length < 2) return 'Full name must be at least 2 characters.';
  if (trimmed.length > 80) return 'Full name must be 80 characters or fewer.';
  return undefined;
}

function validateAdminUsername(value: string): string | undefined {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return 'Username is required.';
  if (trimmed.length < 3) return 'Username must be at least 3 characters.';
  if (trimmed.length > 32) return 'Username must be 32 characters or fewer.';
  if (!/^[a-z0-9_.-]+$/.test(trimmed))
    return 'Username may only contain lowercase letters, numbers, underscores, hyphens, or dots.';
  return undefined;
}

function validateAdminPassword(value: string): string | undefined {
  if (!value) return 'Password is required.';
  if (value.length < 8) return 'Password must be at least 8 characters.';
  if (!/[A-Z]/.test(value)) return 'Password must contain at least one uppercase letter.';
  if (!/[a-z]/.test(value)) return 'Password must contain at least one lowercase letter.';
  if (!/[0-9]/.test(value)) return 'Password must contain at least one number.';
  if (!/[^A-Za-z0-9]/.test(value)) return 'Password must contain at least one special character.';
  return undefined;
}

function validateAdminConfirmPassword(password: string, confirm: string): string | undefined {
  if (!confirm) return 'Please confirm your password.';
  if (password !== confirm) return 'Passwords do not match.';
  return undefined;
}

export function useSetupWizard(options?: UseSetupWizardOptions) {
  const [currentStep, setCurrentStep] = useState<WizardStepId>('workspace');
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStepId>>(new Set());

  const [formData, setFormData] = useState<WizardFormData>({
    workspaceName: options?.initialConfig?.workspaceName || 'Workspace',
    workspacePath: options?.initialConfig?.workspacePath || '',
    theme: options?.initialConfig?.theme || 'light',
    adminFullName: '',
    adminUsername: '',
    adminPassword: '',
    adminConfirmPassword: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [verifiedConfig, setVerifiedConfig] = useState<WorkspaceConfig | null>(null);

  // Touched state for administrator fields (show errors only after interaction)
  const [adminTouched, setAdminTouched] = useState<Record<string, boolean>>({});

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

  // Admin step validations
  const adminFullNameError = validateAdminFullName(formData.adminFullName);
  const adminUsernameError = validateAdminUsername(formData.adminUsername);
  const adminPasswordError = validateAdminPassword(formData.adminPassword);
  const adminConfirmPasswordError = validateAdminConfirmPassword(
    formData.adminPassword,
    formData.adminConfirmPassword
  );

  const isWorkspaceStepValid = workspaceNameValidation.isValid;
  const isAppearanceStepValid = ['light', 'dark', 'system'].includes(formData.theme);
  const isAdminStepValid =
    !adminFullNameError &&
    !adminUsernameError &&
    !adminPasswordError &&
    !adminConfirmPasswordError;
  const isReviewStepValid =
    isWorkspaceStepValid && isStorageStepValid && isAppearanceStepValid && isAdminStepValid;

  const isCurrentStepValid = useMemo(() => {
    switch (currentStep) {
      case 'workspace': return isWorkspaceStepValid;
      case 'storage': return isStorageStepValid;
      case 'appearance': return isAppearanceStepValid;
      case 'administrator': return isAdminStepValid;
      case 'review': return isReviewStepValid;
      default: return false;
    }
  }, [currentStep, isWorkspaceStepValid, isStorageStepValid, isAppearanceStepValid, isAdminStepValid, isReviewStepValid]);

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

  const setAdminField = useCallback((field: keyof WizardFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setSubmitError(null);
  }, []);

  const touchAdminField = useCallback((field: string) => {
    setAdminTouched((prev) => ({ ...prev, [field]: true }));
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
      case 'workspace': setCurrentStep('storage'); break;
      case 'storage': setCurrentStep('appearance'); break;
      case 'appearance': setCurrentStep('administrator'); break;
      case 'administrator': setCurrentStep('review'); break;
      case 'review': break;
    }
  }, [currentStep, isCurrentStepValid]);

  const goBack = useCallback(() => {
    setSubmitError(null);
    switch (currentStep) {
      case 'workspace': break;
      case 'storage': setCurrentStep('workspace'); break;
      case 'appearance': setCurrentStep('storage'); break;
      case 'administrator': setCurrentStep('appearance'); break;
      case 'review': setCurrentStep('administrator'); break;
    }
  }, [currentStep]);

  const finishSetup = useCallback(async () => {
    if (!isReviewStepValid || isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // Build workspace config (without admin fields — they go through the identity command)
      const baseConfig: WorkspaceConfig = {
        schemaVersion: 1,
        workspaceName: formData.workspaceName.trim(),
        workspacePath: formData.workspacePath.trim(),
        theme: formData.theme,
        onboardingCompleted: false, // Rust will set this to true
      };

      // Single IPC: Rust saves workspace config AND hashes + stores admin identity atomically
      const savedConfig = await ipcService.createBootstrapAdmin(
        baseConfig,
        formData.adminFullName.trim(),
        formData.adminUsername.trim().toLowerCase(),
        formData.adminPassword // plaintext — zeroized in Rust immediately after hashing
      );

      setVerifiedConfig(savedConfig);
      setIsReady(true);
      if (options?.onSetupComplete) {
        options.onSetupComplete(savedConfig);
      }
    } catch (err) {
      console.error('Finish setup persistence failed:', err);
      setSubmitError(
        err instanceof Error
          ? err.message
          : 'Failed to save workspace configuration. Please verify storage permissions.'
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
    isAdminStepValid,
    isReviewStepValid,
    isCurrentStepValid,
    workspaceNameError: workspaceNameValidation.error,
    workspacePathError: isStorageTouched ? workspacePathError : undefined,
    adminFullNameError: adminTouched['adminFullName'] ? adminFullNameError : undefined,
    adminUsernameError: adminTouched['adminUsername'] ? adminUsernameError : undefined,
    adminPasswordError: adminTouched['adminPassword'] ? adminPasswordError : undefined,
    adminConfirmPasswordError: adminTouched['adminConfirmPassword'] ? adminConfirmPasswordError : undefined,
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
  };
}
