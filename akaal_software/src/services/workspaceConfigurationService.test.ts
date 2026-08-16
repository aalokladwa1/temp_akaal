import { describe, it, expect, vi } from 'vitest';
import { workspaceConfigurationService, SCHEMA_VERSION } from './workspaceConfigurationService';
import type { WorkspaceConfig } from '../types/workspace';

vi.mock('./ipcService', () => ({
  ipcService: {
    validateWorkspacePath: vi.fn().mockImplementation(async (path: string) => {
      return path.includes('AKAAL') || path.includes('/tmp/test');
    }),
  },
}));

describe('WorkspaceConfigurationService Unit Tests', () => {
  it('validates schema version & default configuration', () => {
    const defaults = workspaceConfigurationService.getDefaultConfig();
    expect(defaults.schemaVersion).toBe(SCHEMA_VERSION);
    expect(defaults.workspaceName).toBe('Workspace');
    expect(defaults.onboardingCompleted).toBe(false);
  });

  it('validates workspace name bounds & illegal characters', () => {
    expect(workspaceConfigurationService.validateWorkspaceName('').isValid).toBe(false);
    expect(workspaceConfigurationService.validateWorkspaceName('   ').isValid).toBe(false);
    expect(workspaceConfigurationService.validateWorkspaceName('Valid Workspace').isValid).toBe(true);
    expect(workspaceConfigurationService.validateWorkspaceName('a'.repeat(101)).isValid).toBe(false);

    expect(workspaceConfigurationService.validateWorkspaceName('Workspace/1').isValid).toBe(false);
    expect(workspaceConfigurationService.validateWorkspaceName('Workspace?').isValid).toBe(false);
  });

  it('validates workspace path formatting', async () => {
    const emptyPathRes = await workspaceConfigurationService.validateWorkspacePath('');
    expect(emptyPathRes.isValid).toBe(false);

    const invalidCharsPathRes = await workspaceConfigurationService.validateWorkspacePath('C:\\invalid|folder');
    expect(invalidCharsPathRes.isValid).toBe(false);

    const validPathRes = await workspaceConfigurationService.validateWorkspacePath('C:\\AKAAL_Workspace');
    expect(validPathRes.isValid).toBe(true);
  });

  it('verifies config match logic', () => {
    const memoryConfig: WorkspaceConfig = {
      schemaVersion: 1,
      workspaceName: 'Test Workspace',
      workspacePath: '/tmp/test',
      theme: 'dark',
      onboardingCompleted: true,
    };

    expect(workspaceConfigurationService.verifyConfig(memoryConfig, { ...memoryConfig })).toBe(true);
    expect(
      workspaceConfigurationService.verifyConfig(memoryConfig, {
        ...memoryConfig,
        workspaceName: 'Different Name',
      })
    ).toBe(false);
  });
});
