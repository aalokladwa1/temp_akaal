/**
 * AKAAL Workspace Configuration Manager Service Layer
 * 
 * Provides isolated frontend configuration management.
 * UI components NEVER invoke Rust IPC commands directly.
 */

import { ipcService } from './ipcService';
import type { WorkspaceConfig, WorkspaceValidationResult } from '../types/workspace';

export const SCHEMA_VERSION = 1;

export const workspaceConfigurationService = {
  getDefaultConfig(): WorkspaceConfig {
    return {
      schemaVersion: SCHEMA_VERSION,
      workspaceName: 'Workspace',
      workspacePath: '',
      theme: 'light',
      onboardingCompleted: false,
    };
  },

  validateWorkspaceName(name: string): WorkspaceValidationResult {
    const trimmed = name.trim();
    if (trimmed.length === 0) {
      return { isValid: false, error: 'Workspace name is required.' };
    }
    if (trimmed.length > 100) {
      return { isValid: false, error: 'Workspace name cannot exceed 100 characters.' };
    }
    const invalidChars = /[<>:"/\\|?*]/;
    if (invalidChars.test(trimmed)) {
      return { isValid: false, error: 'Workspace name contains invalid characters.' };
    }
    return { isValid: true };
  },

  async validateWorkspacePath(path: string): Promise<WorkspaceValidationResult> {
    const trimmed = path.trim();
    if (trimmed.length === 0) {
      return { isValid: false, error: 'Storage location is required.' };
    }

    const invalidChars = /[<>:"|?*]/;
    const pathWithoutDrive = trimmed.replace(/^[a-zA-Z]:/, '');
    if (invalidChars.test(pathWithoutDrive)) {
      return { isValid: false, error: 'Storage location path contains invalid characters.' };
    }

    try {
      const isValid = await ipcService.validateWorkspacePath(trimmed);
      if (!isValid) {
        return { isValid: false, error: 'Storage location path is invalid or unwritable.' };
      }
      return { isValid: true };
    } catch (err: unknown) {
      if (typeof err === 'string') {
        return { isValid: false, error: err };
      }
      if (err instanceof Error) {
        return { isValid: false, error: err.message };
      }
      // In web preview fallback context, validate basic non-empty string format
      if (trimmed.length >= 2) {
        return { isValid: true };
      }
      return { isValid: false, error: 'Invalid directory path.' };
    }
  },

  async load(): Promise<WorkspaceConfig> {
    try {
      const config = await ipcService.loadWorkspaceConfig();
      if (!config || typeof config.schemaVersion !== 'number') {
        return this.getDefaultConfig();
      }
      return config;
    } catch (err) {
      console.warn('ConfigurationManager.load() failed. Utilizing fallback defaults:', err);
      return this.getDefaultConfig();
    }
  },

  async saveAndVerify(config: WorkspaceConfig): Promise<WorkspaceConfig> {
    // 1. Validate inputs before invoking save
    const nameVal = this.validateWorkspaceName(config.workspaceName);
    if (!nameVal.isValid) {
      throw new Error(nameVal.error || 'Invalid workspace name');
    }

    const pathVal = await this.validateWorkspacePath(config.workspacePath);
    if (!pathVal.isValid) {
      throw new Error(pathVal.error || 'Invalid workspace path');
    }

    // 2. Perform Rust atomic write & creation
    try {
      const savedConfig = await ipcService.saveWorkspaceConfig({
        ...config,
        schemaVersion: SCHEMA_VERSION,
        workspaceName: config.workspaceName.trim(),
        workspacePath: config.workspacePath.trim(),
      });

      // 3. Verification check
      const isVerified = this.verifyConfig(config, savedConfig);
      if (!isVerified) {
        throw new Error('Verification failed: Persisted workspace.json values do not match requested configuration.');
      }

      return savedConfig;
    } catch (err) {
      if (err instanceof Error) {
        throw err;
      }
      throw new Error(`Failed to persist workspace configuration: ${String(err)}`);
    }
  },

  verifyConfig(expected: WorkspaceConfig, actual: WorkspaceConfig): boolean {
    return (
      actual.workspaceName === expected.workspaceName.trim() &&
      actual.workspacePath === expected.workspacePath.trim() &&
      actual.theme === expected.theme &&
      actual.onboardingCompleted === true
    );
  },
};
