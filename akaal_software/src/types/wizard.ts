/**
 * AKAAL Setup Wizard Navigation & State Types
 */

import type { ThemePreference } from './workspace';

export type WizardStepId = 'workspace' | 'storage' | 'appearance' | 'review';

export type StepState = 'current' | 'completed' | 'upcoming';

export interface StepDescriptor {
  id: WizardStepId;
  label: string;
}

export interface WizardFormData {
  workspaceName: string;
  workspacePath: string;
  theme: ThemePreference;
}

export interface WizardValidationState {
  workspaceNameError?: string;
  workspacePathError?: string;
  isWorkspaceValid: boolean;
  isStorageValid: boolean;
  isAppearanceValid: boolean;
  isReviewValid: boolean;
}
