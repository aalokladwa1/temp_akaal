import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { NewValidationWizardComponent } from './new-validation-wizard.component';
import { Step1DefinitionComponent } from './steps/step1-definition.component';
import { Step2SourceComponent } from './steps/step2-source.component';
import { Step3TargetComponent } from './steps/step3-target.component';
import { Step4ScopeComponent } from './steps/step4-scope.component';
import { Step5BoundaryComponent } from './steps/step5-boundary.component';
import { ValidationUiService } from '../../../core/services/validation-ui.service';
import { MigrationHomeService } from '../../../core/services/migration-home.service';

describe('NewValidationWizardComponent & Step 1 Definition (8-Step Foundation)', () => {
  let wizard: NewValidationWizardComponent;
  let step1: Step1DefinitionComponent;
  let vs: ValidationUiService;
  let homeService: MigrationHomeService;
  let mockRouter: any;

  beforeEach(() => {
    vs = new ValidationUiService();
    homeService = new MigrationHomeService();
    mockRouter = {
      navigate: vi.fn()
    };

    wizard = new NewValidationWizardComponent(vs, mockRouter);
    step1 = new Step1DefinitionComponent(vs, homeService);

    vs.resetDraft();
  });

  it('should initialize the wizard on Step 1 (Definition)', () => {
    expect(wizard).toBeTruthy();
    expect(wizard.currentStep()).toBe(1);
    expect(wizard.currentStepItem().label).toBe('Definition');
  });

  it('should define the canonical 8-step rail with precise labels', () => {
    expect(wizard.steps.length).toBe(8);
    expect(wizard.steps.map(s => s.label)).toEqual([
      'Definition',
      'Source',
      'Target',
      'Scope',
      'Boundary',
      'Strategy',
      'Readiness',
      'Review'
    ]);
  });

  it('Step 1 should be invalid when validation name is empty', () => {
    vs.updateDraft({ name: '' });
    expect(vs.isStep1Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
    expect(step1.isNameInvalid()).toBe(false); // not touched yet
    step1.nameTouched.set(true);
    expect(step1.isNameInvalid()).toBe(true);
  });

  it('Step 1 should be valid for Independent validation when name is provided', () => {
    step1.onNameChange('Oracle to PG Parity Audit');
    expect(vs.newValidationDraft().name).toBe('Oracle to PG Parity Audit');
    expect(vs.newValidationDraft().validationContext).toBe('INDEPENDENT');
    expect(vs.isStep1Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
    expect(step1.isNameInvalid()).toBe(false);
  });

  it('Step 1 should require a linked project when context is EXISTING_PROJECT', () => {
    step1.onNameChange('Linked Audit');
    step1.setContextType('EXISTING_PROJECT');
    expect(step1.isLinkedToProject()).toBe(true);
    
    // Clear projectId to test validation gate
    vs.updateDraft({ projectId: undefined });
    expect(vs.isStep1Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);

    // Select project
    const proj = homeService.projects()[0];
    step1.selectProject(proj);
    expect(vs.newValidationDraft().projectId).toBe(proj.id);
    expect(vs.newValidationDraft().projectName).toBe(proj.name);
    expect(vs.isStep1Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('should clear linked project state when switching context back to INDEPENDENT', () => {
    step1.onNameChange('Linked Audit');
    step1.setContextType('EXISTING_PROJECT');
    const proj = homeService.projects()[0];
    step1.selectProject(proj);
    expect(vs.newValidationDraft().projectId).toBe(proj.id);

    step1.setContextType('INDEPENDENT');
    expect(step1.isLinkedToProject()).toBe(false);
    expect(vs.newValidationDraft().projectId).toBeUndefined();
    expect(vs.newValidationDraft().projectName).toBeUndefined();
    expect(vs.isStep1Valid()).toBe(true);
  });

  it('should filter projects list by search query', () => {
    const list = step1.availableProjects();
    expect(list.length).toBeGreaterThan(0);

    step1.projectSearchQuery.set('Banking');
    const filtered = step1.filteredProjects();
    expect(filtered.length).toBeGreaterThan(0);
    expect(filtered.every(p => p.name.toLowerCase().includes('banking'))).toBe(true);
  });

  it('should support toggling environment between Production (Red) and Non-Production (Green)', () => {
    step1.selectEnvironment('Production');
    expect(vs.newValidationDraft().environment).toBe('Production');
    expect(step1.getEnvColor('Production')).toBe('bg-rose-500');

    step1.selectEnvironment('Non-Production');
    expect(vs.newValidationDraft().environment).toBe('Non-Production');
    expect(step1.getEnvColor('Non-Production')).toBe('bg-emerald-500');
  });

  it('should allow navigation forward when Step 1 is valid', () => {
    step1.onNameChange('Production Parity Run');
    expect(wizard.isCurrentStepValid()).toBe(true);
    
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(2);
    expect(wizard.currentStepItem().label).toBe('Source');
  });

  it('should block navigation forward when Step 1 is invalid', () => {
    vs.updateDraft({ name: '   ' });
    expect(wizard.isCurrentStepValid()).toBe(false);
    
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(1);
  });

  it('should allow jumping back to completed steps and stepping backward', () => {
    step1.onNameChange('Production Parity Run');
    wizard.continueToNextStep(); // Step 2
    expect(wizard.currentStep()).toBe(2);

    wizard.previousStep();
    expect(wizard.currentStep()).toBe(1);

    wizard.continueToNextStep(); // Step 2
    wizard.goToCompletedStep(1);
    expect(wizard.currentStep()).toBe(1);
  });

  it('should handle clean exit directly without modal', () => {
    expect(vs.newValidationDraft().isDirty).toBe(false);
    wizard.handleExit();
    expect(wizard.showExitModal()).toBe(false);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration/validation']);
  });

  it('should show exit modal if draft is dirty', () => {
    step1.onNameChange('Draft in progress');
    expect(vs.newValidationDraft().isDirty).toBe(true);
    wizard.handleExit();
    expect(wizard.showExitModal()).toBe(true);

    wizard.exitToValidationHome();
    expect(wizard.showExitModal()).toBe(false);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration/validation']);
  });
});

describe('Step 2 Source Instance & Connectivity', () => {
  let wizard: NewValidationWizardComponent;
  let step2: import('./steps/step2-source.component').Step2SourceComponent;
  let vs: ValidationUiService;
  let mockRouter: any;

  beforeEach(async () => {
    vs = new ValidationUiService();
    mockRouter = {
      navigate: vi.fn()
    };

    const { Step2SourceComponent } = await import('./steps/step2-source.component');
    wizard = new NewValidationWizardComponent(vs, mockRouter);
    step2 = new Step2SourceComponent(vs);

    vs.resetDraft();
    vs.updateDraft({ name: 'Validation Test 1', currentStep: 2 });
  });

  it('Step 2 should be initially invalid before mode selection', () => {
    expect(vs.newValidationDraft().sourceConnectionMode).toBeUndefined();
    expect(vs.isStep2Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
  });

  it('should allow switching between SAVED and NEW connection modes', () => {
    step2.setConnectionMode('SAVED');
    expect(vs.newValidationDraft().sourceConnectionMode).toBe('SAVED');

    step2.setConnectionMode('NEW');
    expect(vs.newValidationDraft().sourceConnectionMode).toBe('NEW');
  });

  it('SAVED branch: should filter saved connections by query, environment, and category', () => {
    step2.setConnectionMode('SAVED');
    expect(step2.enterpriseSavedConnections.length).toBeGreaterThan(0);

    // Search query
    step2.savedSearchQuery.set('Oracle');
    expect(step2.filteredSavedConnections().every(c => c.name.includes('Oracle') || c.provider.includes('Oracle') || c.host.includes('Oracle'))).toBe(true);

    // Clear search
    step2.savedSearchQuery.set('');

    // Environment filter
    step2.filterEnvironment.set('Non-Production');
    expect(step2.filteredSavedConnections().every(c => c.environment === 'Non-Production')).toBe(true);

    // Category filter
    step2.filterEnvironment.set('ALL');
    step2.filterCategory.set('WAREHOUSE');
    expect(step2.filteredSavedConnections().every(c => c.category === 'WAREHOUSE')).toBe(true);
  });

  it('SAVED branch: selecting a healthy saved connection sets verified state and makes Step 2 valid', () => {
    step2.setConnectionMode('SAVED');
    const pgConn = step2.enterpriseSavedConnections.find(c => c.provider === 'PostgreSQL' && c.status === 'CONNECTED')!;
    expect(pgConn).toBeDefined();

    step2.selectSavedEndpoint(pgConn);
    expect(vs.newValidationDraft().sourceConnectionId).toBe(pgConn.id);
    expect(vs.newValidationDraft().sourceProvider).toBe('PostgreSQL');
    expect(vs.newValidationDraft().sourceVerified).toBe(true);
    expect(vs.isStep2Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('SAVED branch: selecting a disconnected connection fails evaluation and blocks Step 2', () => {
    step2.setConnectionMode('SAVED');
    const disconnectedConn = step2.enterpriseSavedConnections.find(c => c.status === 'DISCONNECTED')!;
    expect(disconnectedConn).toBeDefined();

    step2.selectSavedEndpoint(disconnectedConn);
    expect(vs.newValidationDraft().sourceConnectionId).toBe(disconnectedConn.id);
    expect(vs.newValidationDraft().sourceVerified).toBe(false);
    expect(vs.isStep2Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
  });

  it('NEW branch: should display 48 database engines and allow category filtering', () => {
    step2.setConnectionMode('NEW');
    expect(step2.catalogEngines.length).toBe(48);

    step2.selectedCategoryTab.set('RELATIONAL');
    expect(step2.filteredCatalogEngines().length).toBe(10);

    step2.selectedCategoryTab.set('DISTRIBUTED_SQL');
    expect(step2.filteredCatalogEngines().length).toBe(5);

    step2.selectedCategoryTab.set('WAREHOUSE');
    expect(step2.filteredCatalogEngines().length).toBe(7);

    step2.selectedCategoryTab.set('NOSQL');
    expect(step2.filteredCatalogEngines().length).toBe(12);

    step2.selectedCategoryTab.set('STREAMING');
    expect(step2.filteredCatalogEngines().length).toBe(6);

    step2.selectedCategoryTab.set('STORAGE');
    expect(step2.filteredCatalogEngines().length).toBe(5);

    step2.selectedCategoryTab.set('SAAS');
    expect(step2.filteredCatalogEngines().length).toBe(3);
  });

  it('NEW branch: selecting engine loads provider schema and sets default port', () => {
    step2.setConnectionMode('NEW');
    step2.selectEngine('PostgreSQL');
    expect(vs.newValidationDraft().sourceProvider).toBe('PostgreSQL');
    expect(vs.newValidationDraft().sourcePort).toBe(5432);
    expect(step2.selectedProviderSchema()?.name).toBe('PostgreSQL');
    expect(vs.newValidationDraft().sourceVerified).toBe(false);
    expect(vs.isStep2Valid()).toBe(false);
  });

  it('NEW branch: provider conditional fields respect visibility rules (Oracle service vs sid)', () => {
    step2.setConnectionMode('NEW');
    step2.selectEngine('Oracle');
    const schema = step2.selectedProviderSchema()!;

    const sidField = schema.fields.find(f => f.id === 'sid')!;
    const svcField = schema.fields.find(f => f.id === 'service_name')!;

    // Default connection_type is SERVICE_NAME -> sid is hidden, service_name is visible
    expect(step2.isFieldVisible(sidField, schema)).toBe(false);
    expect(step2.isFieldVisible(svcField, schema)).toBe(true);

    // Switch connection_type to SID
    step2.onFieldChange('connection_type', 'SID');
    expect(step2.isFieldVisible(sidField, schema)).toBe(true);
    expect(step2.isFieldVisible(svcField, schema)).toBe(false);
  });

  it('NEW branch: 7-phase probe fails Phase 1 when required fields are missing', async () => {
    step2.setConnectionMode('NEW');
    step2.selectEngine('PostgreSQL');
    // Fields are empty
    step2.runSevenPhaseProbe();

    // Wait for first phase execution
    await new Promise(r => setTimeout(r, 250));
    expect(step2.verificationError()?.category).toBe('MISSING_REQUIRED_PARAMETERS');
    expect(vs.newValidationDraft().sourceVerified).toBe(false);
    expect(vs.isStep2Valid()).toBe(false);
  });

  it('NEW branch: 7-phase probe succeeds when required fields are populated', async () => {
    step2.setConnectionMode('NEW');
    step2.selectEngine('PostgreSQL');
    step2.onFieldChange('host', 'pg-prod.internal');
    step2.onFieldChange('port', 5432);
    step2.onFieldChange('database', 'finance_db');
    step2.onFieldChange('username', 'val_user');
    step2.onFieldChange('password', 'vault://secret/prod/pg');

    step2.runSevenPhaseProbe();

    // Wait for full 7 phases to complete (7 * 190ms = ~1400ms)
    await new Promise(r => setTimeout(r, 1600));

    expect(step2.verificationError()).toBeNull();
    expect(vs.newValidationDraft().sourceVerified).toBe(true);
    expect(vs.isStep2Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('NEW branch: should allow saving verified connection to vault', () => {
    step2.setConnectionMode('NEW');
    step2.selectEngine('PostgreSQL');
    vs.updateDraft({
      sourceVerified: true,
      sourceHost: 'pg-prod.internal',
      sourcePort: 5432,
      sourceDatabase: 'finance_db',
      sourceUsername: 'val_user'
    });

    step2.onSaveToVaultChange(true);
    expect(vs.newValidationDraft().sourceSaveToVault).toBe(true);

    step2.onVaultConnectionNameChange('Custom PG Production');
    step2.saveSourceToVault();

    expect(step2.isSourceVaultSaved()).toBe(true);
    expect(step2.enterpriseSavedConnections.some(c => c.name === 'Custom PG Production')).toBe(true);
  });

  it('should allow navigation from Step 2 to Step 3 when Step 2 is valid', () => {
    step2.setConnectionMode('SAVED');
    const pgConn = step2.enterpriseSavedConnections.find(c => c.provider === 'PostgreSQL' && c.status === 'CONNECTED')!;
    step2.selectSavedEndpoint(pgConn);

    expect(wizard.currentStep()).toBe(2);
    expect(wizard.isCurrentStepValid()).toBe(true);

    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(3);
    expect(wizard.currentStepItem().label).toBe('Target');
  });
});

describe('Step 3 Target Instance & Compatibility (48 Providers, Read Attestation & Guard)', () => {
  let wizard: NewValidationWizardComponent;
  let step3: any;
  let vs: ValidationUiService;
  let mockRouter: any;

  beforeEach(async () => {
    vs = new ValidationUiService();
    mockRouter = {
      navigate: vi.fn()
    };

    const { Step3TargetComponent } = await import('./steps/step3-target.component');
    wizard = new NewValidationWizardComponent(vs, mockRouter);
    step3 = new Step3TargetComponent(vs);

    vs.resetDraft();
    vs.updateDraft({
      name: 'Validation Test Step 3',
      currentStep: 3,
      sourceConnectionMode: 'SAVED',
      sourceConnectionId: 'conn-01',
      sourceProvider: 'Oracle',
      sourceHost: 'ora-rac-cluster.prod.internal',
      sourcePort: 1521,
      sourceDatabase: 'ORCLPDB',
      sourceVerified: true
    });
  });

  it('Step 3 should be initially invalid before target mode selection', () => {
    expect(vs.newValidationDraft().targetConnectionMode).toBeUndefined();
    expect(vs.isStep3Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
  });

  it('should allow switching between SAVED and NEW connection modes for Target', () => {
    step3.setConnectionMode('SAVED');
    expect(vs.newValidationDraft().targetConnectionMode).toBe('SAVED');

    step3.setConnectionMode('NEW');
    expect(vs.newValidationDraft().targetConnectionMode).toBe('NEW');
  });

  it('SAVED branch: should filter saved target connections by query, environment, and category', () => {
    step3.setConnectionMode('SAVED');
    expect(step3.enterpriseSavedConnections.length).toBeGreaterThan(0);

    // Search query
    step3.savedSearchQuery.set('Aurora');
    expect(step3.filteredSavedConnections().every((c: any) => c.name.includes('Aurora') || c.host.includes('aurora'))).toBe(true);

    // Clear search
    step3.savedSearchQuery.set('');

    // Environment filter
    step3.filterEnvironment.set('Non-Production');
    expect(step3.filteredSavedConnections().every((c: any) => c.environment === 'Non-Production')).toBe(true);

    // Category filter
    step3.filterEnvironment.set('ALL');
    step3.filterCategory.set('WAREHOUSE');
    expect(step3.filteredSavedConnections().every((c: any) => c.category === 'WAREHOUSE')).toBe(true);
  });

  it('SAVED branch: selecting a healthy saved connection sets verified state and makes Step 3 valid', () => {
    step3.setConnectionMode('SAVED');
    const pgConn = step3.enterpriseSavedConnections.find((c: any) => c.provider === 'PostgreSQL' && c.status === 'CONNECTED')!;
    expect(pgConn).toBeDefined();

    step3.selectSavedEndpoint(pgConn);
    expect(vs.newValidationDraft().targetConnectionId).toBe(pgConn.id);
    expect(vs.newValidationDraft().targetProvider).toBe('PostgreSQL');
    expect(vs.newValidationDraft().targetVerified).toBe(true);
    expect(vs.isStep3Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('SAVED branch: selecting a disconnected saved connection keeps Step 3 invalid', () => {
    step3.setConnectionMode('SAVED');
    const disconnectedConn = step3.enterpriseSavedConnections.find((c: any) => c.status === 'DISCONNECTED')!;
    expect(disconnectedConn).toBeDefined();

    step3.selectSavedEndpoint(disconnectedConn);
    expect(vs.newValidationDraft().targetConnectionId).toBe(disconnectedConn.id);
    expect(vs.newValidationDraft().targetVerified).toBe(false);
    expect(vs.isStep3Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
  });

  it('NEW branch: should display 48 database engines and allow 7-category filtering', () => {
    step3.setConnectionMode('NEW');
    expect(step3.catalogEngines.length).toBe(48);

    step3.selectedCategoryTab.set('RELATIONAL');
    expect(step3.filteredCatalogEngines().length).toBe(10);

    step3.selectedCategoryTab.set('DISTRIBUTED_SQL');
    expect(step3.filteredCatalogEngines().length).toBe(5);

    step3.selectedCategoryTab.set('WAREHOUSE');
    expect(step3.filteredCatalogEngines().length).toBe(7);

    step3.selectedCategoryTab.set('NOSQL');
    expect(step3.filteredCatalogEngines().length).toBe(12);

    step3.selectedCategoryTab.set('STREAMING');
    expect(step3.filteredCatalogEngines().length).toBe(6);

    step3.selectedCategoryTab.set('STORAGE');
    expect(step3.filteredCatalogEngines().length).toBe(5);

    step3.selectedCategoryTab.set('SAAS');
    expect(step3.filteredCatalogEngines().length).toBe(3);
  });

  it('NEW branch: selecting engine loads provider schema and sets default port', () => {
    step3.setConnectionMode('NEW');
    step3.selectEngine('Snowflake');
    expect(vs.newValidationDraft().targetProvider).toBe('Snowflake');
    expect(vs.newValidationDraft().targetPort).toBe(443);
    expect(step3.selectedProviderSchema()?.name).toBe('Snowflake Data Cloud');
    expect(vs.newValidationDraft().targetVerified).toBe(false);
    expect(vs.isStep3Valid()).toBe(false);
  });

  it('NEW branch: provider conditional fields respect visibility rules', () => {
    step3.setConnectionMode('NEW');
    step3.selectEngine('Oracle');
    const schema = step3.selectedProviderSchema()!;

    const sidField = schema.fields.find((f: any) => f.id === 'sid')!;
    const svcField = schema.fields.find((f: any) => f.id === 'service_name')!;

    // Default connection_type is SERVICE_NAME -> sid is hidden, service_name is visible
    expect(step3.isFieldVisible(sidField, schema)).toBe(false);
    expect(step3.isFieldVisible(svcField, schema)).toBe(true);

    // Switch connection_type to SID
    step3.onFieldChange('connection_type', 'SID');
    expect(step3.isFieldVisible(sidField, schema)).toBe(true);
    expect(step3.isFieldVisible(svcField, schema)).toBe(false);
  });

  it('NEW branch: 6-phase read probe fails Phase 1 when required fields are missing', async () => {
    step3.setConnectionMode('NEW');
    step3.selectEngine('PostgreSQL');
    // Required fields are empty
    step3.runTargetReadProbe();

    await new Promise(r => setTimeout(r, 250));
    expect(step3.verificationError()?.category).toBe('MISSING_REQUIRED_PARAMETERS');
    expect(vs.newValidationDraft().targetVerified).toBe(false);
    expect(vs.isStep3Valid()).toBe(false);
  });

  it('NEW branch: 6-phase read probe succeeds when required fields are populated', async () => {
    step3.setConnectionMode('NEW');
    step3.selectEngine('PostgreSQL');
    step3.onFieldChange('host', 'aurora-pg.target.internal');
    step3.onFieldChange('port', 5432);
    step3.onFieldChange('database', 'target_ledger');
    step3.onFieldChange('username', 'val_read_user');
    step3.onFieldChange('password', 'vault://secret/prod/target/pg');

    step3.runTargetReadProbe();

    // Wait for 6 phases (6 * 180ms = ~1100ms)
    await new Promise(r => setTimeout(r, 1400));

    expect(step3.verificationError()).toBeNull();
    expect(vs.newValidationDraft().targetVerified).toBe(true);
    expect(vs.isStep3Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('Same-Endpoint Guard: detects when Source and Target reference the exact same endpoint', () => {
    step3.setConnectionMode('SAVED');
    // Source was set to conn-01 in beforeEach
    step3.selectSavedEndpoint({
      id: 'conn-01',
      name: 'Oracle 19c Enterprise RAC',
      provider: 'Oracle',
      category: 'RELATIONAL',
      environment: 'Production',
      host: 'ora-rac-cluster.prod.internal',
      port: 1521,
      status: 'CONNECTED',
      networkRoute: 'DIRECT'
    });

    expect(step3.isSameEndpoint()).toBe(true);

    // Change target to a different connection
    step3.selectSavedEndpoint({
      id: 'conn-02',
      name: 'AWS Aurora PostgreSQL Cluster',
      provider: 'PostgreSQL',
      category: 'RELATIONAL',
      environment: 'Production',
      host: 'aurora-pg-cluster.aws.internal',
      port: 5432,
      status: 'CONNECTED',
      networkRoute: 'PRIVATE_ENDPOINT'
    });

    expect(step3.isSameEndpoint()).toBe(false);
  });

  it('Migration-Linked Candidate Context: detects candidate target when linked to existing project', () => {
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01',
      projectName: 'Cloud Modernization 2026'
    });

    const candidate = step3.projectTargetCandidate();
    expect(candidate).toBeTruthy();
    expect(candidate?.engine).toBe('PostgreSQL');

    step3.applyCandidateTarget(candidate!);
    expect(vs.newValidationDraft().targetProvider).toBe('PostgreSQL');
    expect(vs.newValidationDraft().targetHost).toBe('aurora-pg-01.aws');
    expect(vs.newValidationDraft().targetPort).toBe(5432);
  });

  it('NEW branch: should allow saving verified target connection to vault', () => {
    step3.setConnectionMode('NEW');
    step3.selectEngine('PostgreSQL');
    vs.updateDraft({
      targetVerified: true,
      targetHost: 'aurora-pg.target.internal',
      targetPort: 5432,
      targetDatabase: 'target_ledger',
      targetUsername: 'val_read_user'
    });

    step3.onSaveToVaultChange(true);
    expect(vs.newValidationDraft().targetSaveToVault).toBe(true);

    step3.onVaultConnectionNameChange('Custom Aurora PG Target');
    step3.saveTargetToVault();

    expect(step3.isTargetVaultSaved()).toBe(true);
    expect(step3.enterpriseSavedConnections.some((c: any) => c.name === 'Custom Aurora PG Target')).toBe(true);
  });

  it('Navigation: allows backward jump to Step 2 and continue to Step 4 when Step 3 is valid', () => {
    step3.setConnectionMode('SAVED');
    const pgConn = step3.enterpriseSavedConnections.find((c: any) => c.provider === 'PostgreSQL' && c.status === 'CONNECTED')!;
    step3.selectSavedEndpoint(pgConn);

    expect(wizard.currentStep()).toBe(3);
    expect(wizard.isCurrentStepValid()).toBe(true);

    // Can go back to Step 2
    wizard.previousStep();
    expect(wizard.currentStep()).toBe(2);
    expect(wizard.currentStepItem().label).toBe('Source');

    // Return to Step 3
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(3);

    // Advance to Step 4
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(4);
    expect(wizard.currentStepItem().label).toBe('Scope');
  });
});

describe('Step 4 Scope & Correspondence (Three Pathways, Law 6 Non-Blocking, Decisions Workbench & Gating)', () => {
  let wizard: NewValidationWizardComponent;
  let step4: Step4ScopeComponent;
  let vs: ValidationUiService;
  let mockRouter: any;

  beforeEach(() => {
    vs = new ValidationUiService();
    mockRouter = {
      navigate: vi.fn()
    };

    wizard = new NewValidationWizardComponent(vs, mockRouter);
    vs.resetDraft();
    vs.updateDraft({
      name: 'Validation Test Step 4',
      currentStep: 4,
      sourceConnectionMode: 'SAVED',
      sourceConnectionId: 'conn-01',
      sourceProvider: 'Oracle',
      sourceHost: 'ora-rac-cluster.prod.internal',
      sourcePort: 1521,
      sourceDatabase: 'FINANCE',
      sourceVerified: true,
      targetConnectionMode: 'SAVED',
      targetConnectionId: 'conn-02',
      targetProvider: 'PostgreSQL',
      targetHost: 'aurora-pg-cluster.aws.internal',
      targetPort: 5432,
      targetDatabase: 'public',
      targetVerified: true
    });

    step4 = new Step4ScopeComponent(vs);
    step4.ngOnInit();
  });

  it('Step 4 initializes in CHOICE pathway for INDEPENDENT context and is initially invalid', () => {
    expect(vs.newValidationDraft().validationContext).toBe('INDEPENDENT');
    expect(step4.currentPathway()).toBe('CHOICE');
    expect(vs.isStep4Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
  });

  it('Pathway A (Inherited Migration Scope): auto-inherits migration scope when linked to existing project', () => {
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01',
      projectName: 'Cloud Modernization 2026'
    });
    step4.ngOnInit();

    expect(step4.currentPathway()).toBe('INHERIT');
    expect(step4.units().length).toBeGreaterThan(0);
    expect(step4.includedUnitsCount()).toBe(step4.units().length);
    expect(step4.executionSummary().completedUnits).toBe(300);
    expect(step4.decisionsRequiredCount()).toBe(0);

    // LAW 6: 1 target is NOT currently discovered physically, but Step 4 is STILL VALID!
    expect(step4.notDiscoveredTargetsCount()).toBe(1);
    expect(vs.isStep4Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('LAW 6: Known expected target physically missing remains in scope and does NOT block Step 4', () => {
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01',
      projectName: 'Cloud Modernization 2026'
    });
    step4.ngOnInit();

    const missingUnit = step4.units().find(u => u.observationStatus === 'NOT_DISCOVERED');
    expect(missingUnit).toBeDefined();
    expect(missingUnit!.sourceName).toBe('AUDIT_LOG_2025');
    expect(missingUnit!.disposition).toBe('INCLUDED');

    // Validation wizard allows proceeding because missing target will be verified at execution time
    expect(vs.isStep4Valid()).toBe(true);
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(5);
  });

  it('Pathway B: selecting Import Metadata transitions to truthful unavailable state', () => {
    expect(step4.currentPathway()).toBe('CHOICE');
    step4.setPathway('IMPORT');

    expect(step4.currentPathway()).toBe('IMPORT');
    expect(vs.isStep4Valid()).toBe(false);

    // Can return to options
    step4.setPathway('CHOICE');
    expect(step4.currentPathway()).toBe('CHOICE');
  });

  it('Pathway C: Define Correspondence initializes catalog discovery scope and rules', () => {
    step4.setPathway('DEFINE');
    expect(step4.currentPathway()).toBe('DEFINE');
    expect(step4.units().length).toBeGreaterThan(0);
    expect(step4.selectedSourceNamespace()).toBe('ALL');
    expect(step4.selectedTargetNamespace()).toBe('public');
    expect(step4.selectedCorrespondenceRule()).toBe('EXACT_IDENTIFIER_MATCH');
  });

  it('Decisions Required Workbench: unmapped unit blocks validation until resolved or excluded', () => {
    step4.setPathway('DEFINE');
    // Initially has 1 unmapped legacy customer unit requiring decision
    expect(step4.decisionsRequiredCount()).toBe(1);
    expect(vs.isStep4Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);

    // Case 1: Resolve decision with counterpart selection
    const decisionItem = step4.decisionsList()[0];
    step4.onSelectDecisionTarget(decisionItem.unitId, { target: { value: 'customers' } } as any);

    expect(step4.decisionsRequiredCount()).toBe(0);
    expect(vs.isStep4Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('Decisions Required Workbench: operator can exclude unmapped unit from validation scope', () => {
    step4.setPathway('DEFINE');
    expect(step4.decisionsRequiredCount()).toBe(1);

    const decisionItem = step4.decisionsList()[0];
    step4.excludeDecisionUnit(decisionItem.unitId);

    expect(step4.decisionsRequiredCount()).toBe(0);
    expect(vs.isStep4Valid()).toBe(true);
  });

  it('Decisions Workbench: Change Decision button re-opens decision allowing re-selection of target counterpart', () => {
    step4.setPathway('DEFINE');
    expect(step4.decisionsRequiredCount()).toBe(1);

    const decisionItem = step4.decisionsList()[0];
    // 1. Operator selects a target counterpart
    step4.onSelectDecisionTargetCustom(decisionItem.unitId, 'customers');
    expect(step4.decisionsRequiredCount()).toBe(0);
    expect(vs.isStep4Valid()).toBe(true);
    expect(step4.operatorDecisions().length).toBe(1);
    expect(step4.operatorDecisions()[0].expectedTargetName).toBe('customers');

    // 2. Operator changes mind and clicks Change Decision
    step4.reopenDecision(decisionItem.unitId);
    expect(step4.decisionsRequiredCount()).toBe(1);
    expect(vs.isStep4Valid()).toBe(false);

    // 3. Operator chooses a different target counterpart
    step4.onSelectDecisionTargetCustom(decisionItem.unitId, 'customers_legacy_v2');
    expect(step4.decisionsRequiredCount()).toBe(0);
    expect(vs.isStep4Valid()).toBe(true);
    expect(step4.operatorDecisions()[0].expectedTargetName).toBe('customers_legacy_v2');
  });

  it('Column Correspondence View: search filters columns by name and type', () => {
    step4.setPathway('DEFINE');
    const unit = step4.units()[0];
    step4.openColumnDrawer(unit);
    expect(step4.activeColumnDrawerPair()).toBe(unit);

    // Initial unfiltered count
    const initialCount = step4.filteredColumns().length;
    expect(initialCount).toBeGreaterThan(1);

    // Filter by column name
    step4.columnSearchQuery.set('ID');
    expect(step4.filteredColumns().length).toBe(1);
    expect(step4.filteredColumns()[0].sourceColumn).toContain('ID');

    // Filter by datatype
    step4.columnSearchQuery.set('varchar');
    expect(step4.filteredColumns().length).toBeGreaterThanOrEqual(1);

    // Reset filter
    step4.columnSearchQuery.set('');
    expect(step4.filteredColumns().length).toBe(initialCount);

    step4.closeColumnDrawer();
    expect(step4.activeColumnDrawerPair()).toBeNull();
  });

  it('Custom Select Options: provides structured options for Source Namespace, Target Namespace, and Rules', () => {
    step4.setPathway('DEFINE');
    expect(step4.sourceNamespaceOptions.length).toBeGreaterThanOrEqual(3);
    expect(step4.targetNamespaceOptions.length).toBeGreaterThanOrEqual(2);
    expect(step4.correspondenceRuleOptions.length).toBeGreaterThanOrEqual(3);

    const decisionItem = step4.decisionsList()[0];
    const candidateOpts = step4.getDecisionCandidateOptions(decisionItem);
    expect(candidateOpts.length).toBeGreaterThanOrEqual(2);
    expect(candidateOpts.some(o => o.value === 'customers_legacy')).toBe(true);
  });

  it('Customize Scope Modal: include/exclude units and empty scope validation check', () => {
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01'
    });
    step4.ngOnInit();

    expect(step4.isCustomizeModalOpen()).toBe(false);
    step4.openCustomizeModal();
    expect(step4.isCustomizeModalOpen()).toBe(true);

    // Deselect all units
    step4.deselectAllCustomUnits();
    expect(step4.includedUnitsCount()).toBe(0);
    expect(vs.isStep4Valid()).toBe(false); // Cannot validate empty scope

    // Re-select all units
    step4.selectAllCustomUnits();
    expect(step4.includedUnitsCount()).toBe(step4.units().length);
    expect(vs.isStep4Valid()).toBe(true);

    step4.closeCustomizeModal();
    expect(step4.isCustomizeModalOpen()).toBe(false);
  });

  it('Inspect Scope Drawer: opens manifest table and secondary column drawer', () => {
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01'
    });
    step4.ngOnInit();

    expect(step4.isInspectDrawerOpen()).toBe(false);
    step4.openInspectDrawer();
    expect(step4.isInspectDrawerOpen()).toBe(true);

    // Filter units in drawer
    step4.inspectSearchQuery = 'ACCOUNTS';
    expect(step4.filteredInspectUnits().length).toBe(1);
    step4.inspectSearchQuery = '';

    // Open Column Drawer for first unit
    const unit = step4.units()[0];
    step4.openColumnDrawer(unit);
    expect(step4.activeColumnDrawerPair()).toBe(unit);

    const cols = step4.defaultColumnsForPair(unit);
    expect(cols.length).toBeGreaterThan(0);
    expect(cols.some(c => c.isPrimaryKey)).toBe(true);

    step4.closeColumnDrawer();
    expect(step4.activeColumnDrawerPair()).toBeNull();

    step4.closeInspectDrawer();
    expect(step4.isInspectDrawerOpen()).toBe(false);
  });

  it('State Invalidation: changing Source resets scope; changing Target requires re-evaluation', () => {
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01'
    });
    step4.ngOnInit();
    expect(vs.isStep4Valid()).toBe(true);

    // Changing Target endpoint invalidates correspondence
    vs.updateDraft({ targetHost: 'new-target-pg.corp' });
    expect(vs.isStep4Valid()).toBe(false);

    // Changing Source endpoint completely wipes scope
    vs.updateDraft({ sourceHost: 'new-source-oracle.corp' });
    expect(vs.newValidationDraft().comparisonUnits?.length).toBe(0);
    expect(vs.isStep4Valid()).toBe(false);
  });

  it('Navigation: Step 4 is gated until valid, then allows advancing to Step 5', () => {
    expect(wizard.currentStep()).toBe(4);
    expect(wizard.isCurrentStepValid()).toBe(false);

    // Try to advance while invalid
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(4);

    // Switch to Existing Project (valid)
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01'
    });
    step4.ngOnInit();
    expect(wizard.isCurrentStepValid()).toBe(true);

    // Back to Step 3
    wizard.previousStep();
    expect(wizard.currentStep()).toBe(3);

    // Forward to Step 4
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(4);

    // Forward to Step 5 (Boundary)
    wizard.continueToNextStep();
    expect(wizard.currentStep()).toBe(5);
    expect(wizard.currentStepItem().label).toBe('Boundary');
  });
});

describe('Step 5 Boundary & Consistency Baseline Component', () => {
  let wizard: NewValidationWizardComponent;
  let step5: Step5BoundaryComponent;
  let vs: ValidationUiService;
  let mockRouter: any;

  beforeEach(() => {
    vs = new ValidationUiService();
    mockRouter = {
      navigate: vi.fn()
    };
    wizard = new NewValidationWizardComponent(vs, mockRouter);
    step5 = new Step5BoundaryComponent(vs);
    vs.resetDraft();
  });

  it('State A: Existing Project inherits migration baseline automatically', () => {
    vs.updateDraft({
      validationContext: 'EXISTING_PROJECT',
      projectId: 'proj-01',
      projectName: 'Core Financials Migration',
      currentStep: 5
    });

    step5.ngOnInit();

    expect(step5.isInheritedMode()).toBe(true);
    expect(vs.newValidationDraft().baselineIntent).toBe('INHERITED_MIGRATION');
    expect(vs.isStep5Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
    expect(step5.baselineCardSummary().title).toBe('Inherited Migration Baseline');
  });

  it('State C: Independent Validation starts unselected and fail-closed', () => {
    vs.updateDraft({
      validationContext: 'INDEPENDENT',
      currentStep: 5
    });

    step5.ngOnInit();

    expect(step5.isInheritedMode()).toBe(false);
    expect(vs.newValidationDraft().baselineIntent).toBeUndefined();
    expect(vs.isStep5Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
    expect(step5.baselineConceptCards().length).toBe(5);
  });

  it('State C: Selecting Current Operational baseline satisfies Step 5 gate', () => {
    vs.updateDraft({
      validationContext: 'INDEPENDENT',
      currentStep: 5
    });
    step5.ngOnInit();

    step5.selectIntent('CURRENT_OPERATIONAL');

    expect(vs.newValidationDraft().baselineIntent).toBe('CURRENT_OPERATIONAL');
    expect(vs.isStep5Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
    expect(step5.isMaintenanceSelected()).toBe(false);
  });

  it('State C: Selecting Static / Immutable baseline satisfies Step 5 gate', () => {
    vs.updateDraft({
      validationContext: 'INDEPENDENT',
      currentStep: 5
    });
    step5.ngOnInit();

    step5.selectIntent('STATIC_IMMUTABLE');

    expect(vs.newValidationDraft().baselineIntent).toBe('STATIC_IMMUTABLE');
    expect(vs.isStep5Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);
  });

  it('State C: Maintenance baseline requires operator condition declaration (fail-closed)', () => {
    vs.updateDraft({
      validationContext: 'INDEPENDENT',
      currentStep: 5
    });
    step5.ngOnInit();

    step5.selectIntent('MAINTENANCE_COORDINATED');
    expect(step5.isMaintenanceSelected()).toBe(true);
    // Unselected maintenance condition => gate closed
    expect(vs.newValidationDraft().maintenanceCondition).toBeUndefined();
    expect(vs.isStep5Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);

    // Operator selects writes stopped condition
    step5.selectMaintenanceCondition('WRITES_STOPPED_DECLARED');
    expect(vs.newValidationDraft().maintenanceCondition).toBe('WRITES_STOPPED_DECLARED');
    expect(vs.isStep5Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);

    // Operator switches to external coordination condition
    step5.selectMaintenanceCondition('EXTERNAL_COORDINATION_DECLARED');
    expect(vs.newValidationDraft().maintenanceCondition).toBe('EXTERNAL_COORDINATION_DECLARED');
    expect(vs.isStep5Valid()).toBe(true);
    expect(wizard.isCurrentStepValid()).toBe(true);

    // Operator adds notes
    step5.onNotesChange('Window approved for CR-9812');
    expect(vs.newValidationDraft().operatorNotes).toBe('Window approved for CR-9812');
  });

  it('State D: External Replication baseline is unsupported and strictly fail-closed', () => {
    vs.updateDraft({
      validationContext: 'INDEPENDENT',
      currentStep: 5
    });
    step5.ngOnInit();

    const extOption = step5.baselineConceptCards().find(c => c.id === 'EXTERNAL_REPLICATION');
    expect(extOption?.isSupported).toBe(false);

    step5.selectIntent('EXTERNAL_REPLICATION');
    expect(vs.newValidationDraft().baselineIntent).toBe('EXTERNAL_REPLICATION');
    // Gate remains closed
    expect(vs.isStep5Valid()).toBe(false);
    expect(wizard.isCurrentStepValid()).toBe(false);
    expect(step5.isInsufficientBaseline()).toBe(true);
  });

  it('Technical Details progressive disclosure toggles and provides read-only insight', () => {
    expect(step5.isTechnicalDetailsOpen()).toBe(false);
    step5.toggleTechnicalDetails();
    expect(step5.isTechnicalDetailsOpen()).toBe(true);

    const details = step5.technicalDetails();
    expect(details.length).toBe(6);
    expect(details.some(d => d.key === 'EVIDENCE_RECORDING')).toBe(true);
    expect(details.some(d => d.key === 'FAIL_CLOSED_RESTART')).toBe(true);

    step5.toggleTechnicalDetails();
    expect(step5.isTechnicalDetailsOpen()).toBe(false);
  });

  it('Upstream Invalidation: changing Source or Target resets baseline selection in Independent mode', () => {
    vs.updateDraft({
      validationContext: 'INDEPENDENT',
      currentStep: 5,
      sourceHost: 'oracle-prod.internal',
      targetHost: 'postgres-prod.internal'
    });
    step5.ngOnInit();
    step5.selectIntent('CURRENT_OPERATIONAL');
    expect(vs.isStep5Valid()).toBe(true);

    // Target change resets Step 5 baseline
    vs.updateDraft({ targetHost: 'postgres-staging.internal' });
    expect(vs.newValidationDraft().baselineIntent).toBeUndefined();
    expect(vs.isStep5Valid()).toBe(false);

    // Re-select baseline
    step5.selectIntent('STATIC_IMMUTABLE');
    expect(vs.isStep5Valid()).toBe(true);

    // Source change resets Step 5 baseline
    vs.updateDraft({ sourceHost: 'oracle-dr.internal' });
    expect(vs.newValidationDraft().baselineIntent).toBeUndefined();
    expect(vs.isStep5Valid()).toBe(false);
  });
});



