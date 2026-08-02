import { workspaceConfigurationService, SCHEMA_VERSION } from './workspaceConfigurationService';
import type { WorkspaceConfig } from '../types/workspace';

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`Assertion Failed: ${message}`);
  }
}

export async function runWorkspaceConfigurationServiceTests() {
  // Test 1: Default config schema version & defaults
  const defaults = workspaceConfigurationService.getDefaultConfig();
  assert(defaults.schemaVersion === SCHEMA_VERSION, 'schemaVersion matches default');
  assert(defaults.workspaceName === 'Workspace', 'default workspaceName matches');
  assert(defaults.onboardingCompleted === false, 'default onboardingCompleted is false');

  // Test 2: Validation bounds
  assert(!workspaceConfigurationService.validateWorkspaceName('').isValid, 'empty name invalid');
  assert(!workspaceConfigurationService.validateWorkspaceName('   ').isValid, 'whitespace name invalid');
  assert(workspaceConfigurationService.validateWorkspaceName('Valid Workspace').isValid, 'valid name passes');
  assert(!workspaceConfigurationService.validateWorkspaceName('a'.repeat(101)).isValid, 'long name invalid');

  // Test 3: Illegal characters
  assert(!workspaceConfigurationService.validateWorkspaceName('Workspace/1').isValid, 'slash invalid');
  assert(!workspaceConfigurationService.validateWorkspaceName('Workspace?').isValid, 'question mark invalid');

  // Test 4: Workspace path validation tests
  const emptyPathRes = await workspaceConfigurationService.validateWorkspacePath('');
  assert(!emptyPathRes.isValid, 'empty path invalid');

  const invalidCharsPathRes = await workspaceConfigurationService.validateWorkspacePath('C:\\invalid|folder');
  assert(!invalidCharsPathRes.isValid, 'invalid character in path fails validation');

  const validPathRes = await workspaceConfigurationService.validateWorkspacePath('C:\\AKAAL_Workspace');
  assert(validPathRes.isValid, 'valid path format passes validation');

  // Test 5: Verification logic
  const memoryConfig: WorkspaceConfig = {
    schemaVersion: 1,
    workspaceName: 'Test Workspace',
    workspacePath: '/tmp/test',
    theme: 'dark',
    onboardingCompleted: true,
  };

  assert(
    workspaceConfigurationService.verifyConfig(memoryConfig, { ...memoryConfig }),
    'identical configs verify successfully'
  );

  assert(
    !workspaceConfigurationService.verifyConfig(memoryConfig, {
      ...memoryConfig,
      workspaceName: 'Different Name',
    }),
    'mismatched configs fail verification'
  );
}

// Run unit test assertions during module initialization
runWorkspaceConfigurationServiceTests().catch((err) => {
  console.error('WorkspaceConfigurationService unit tests failed:', err);
});

