/**
 * AKAAL Setup Wizard Navigation & State Types
 */

import type { ThemePreference } from './workspace';

export type WizardStepId =
  | 'workspace'
  | 'storage'
  | 'appearance'
  | 'administrator'
  | 'review';

export type StepState = 'current' | 'completed' | 'upcoming';

export interface StepDescriptor {
  id: WizardStepId;
  label: string;
}

export interface WizardFormData {
  workspaceName: string;
  workspacePath: string;
  theme: ThemePreference;
  adminFullName: string;
  adminUsername: string;
  adminPassword: string;
  adminConfirmPassword: string;
}

export interface WizardValidationState {
  workspaceNameError?: string;
  workspacePathError?: string;
  adminFullNameError?: string;
  adminUsernameError?: string;
  adminPasswordError?: string;
  adminConfirmPasswordError?: string;
  isWorkspaceValid: boolean;
  isStorageValid: boolean;
  isAppearanceValid: boolean;
  isAdminValid: boolean;
  isReviewValid: boolean;
}
