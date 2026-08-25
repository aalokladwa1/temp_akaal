/**
 * AKAAL Enterprise Workspace Configuration Types
 */

export type ThemePreference = 'light' | 'dark' | 'system';

export interface WorkspaceConfig {
  schemaVersion: number;
  workspaceName: string;
  workspacePath: string;
  theme: ThemePreference;
  onboardingCompleted: boolean;
  ownerDisplayName?: string;
  adminUsername?: string;
  hasAdminConfigured?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface WorkspaceValidationResult {
  isValid: boolean;
  error?: string;
}

export interface DirectoryPathResult {
  path: string;
  exists: boolean;
  writable: boolean;
  availableDiskSpaceBytes?: number;
}
