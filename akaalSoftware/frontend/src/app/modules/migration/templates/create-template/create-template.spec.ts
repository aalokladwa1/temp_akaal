import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Router } from '@angular/router';
import { CreateTemplateService } from './create-template.service';
import { TemplatesService } from '../templates.service';
import { CREATE_TEMPLATE_STEPS } from './create-template.models';
import { TEMPLATE_MODE_DESCRIPTORS } from '../templates.models';
import { CreateTemplateComponent } from './create-template.component';
import { Step1DefinitionComponent } from './steps/step1-definition.component';
import { Step2DefaultsComponent } from './steps/step2-defaults.component';
import { Step3ScopeMappingComponent } from './steps/step3-scope-mapping.component';
import { Step4EnterpriseConfigComponent } from './steps/step4-enterprise-config.component';
import { Step5GovernanceReuseComponent } from './steps/step5-governance-reuse.component';
import { Step6ReviewComponent } from './steps/step6-review.component';

describe('Part B: Create Template Workflow', () => {
  let service: CreateTemplateService;
  let templatesService: TemplatesService;
  let routerMock: any;

  beforeEach(() => {
    routerMock = {
      navigate: vi.fn().mockResolvedValue(true)
    };
    templatesService = new TemplatesService();
    templatesService.reload();
    service = new CreateTemplateService(routerMock as unknown as Router, templatesService);
    service.resetDraft();
  });

  // =========================================================================
  // 1. SHELL & STEPPER CONTRACT TESTS
  // =========================================================================
  describe('1. Shell & Stepper Progression', () => {
    it('initializes on Step 1 with clean initial state', () => {
      expect(service.currentStep()).toBe(1);
      expect(CREATE_TEMPLATE_STEPS.length).toBe(6);
      expect(CREATE_TEMPLATE_STEPS[0].label).toBe('Definition & Applicability');
      expect(CREATE_TEMPLATE_STEPS[5].label).toBe('Review & Create');
    });

    it('blocks forward transition when step 1 validation fails (empty name)', () => {
      service.updateDefinition({ name: '   ' });
      expect(service.canProceed()).toBe(false);
      expect(service.validationErrors()).toContain('Template Name is required.');

      service.nextStep();
      expect(service.currentStep()).toBe(1); // Stay on step 1
    });

    it('advances through all 6 steps consecutively when valid', () => {
      service.updateDefinition({ name: 'Oracle to Snowflake Core Template' });
      expect(service.canProceed()).toBe(true);

      // Step 1 -> 2
      service.nextStep();
      expect(service.currentStep()).toBe(2);
      expect(service.isStepComplete(1)).toBe(true);

      // Step 2 -> 3
      service.nextStep();
      expect(service.currentStep()).toBe(3);
      expect(service.isStepComplete(2)).toBe(true);

      // Step 3 -> 4
      service.nextStep();
      expect(service.currentStep()).toBe(4);
      expect(service.isStepComplete(3)).toBe(true);

      // Step 4 -> 5
      service.nextStep();
      expect(service.currentStep()).toBe(5);
      expect(service.isStepComplete(4)).toBe(true);

      // Step 5 -> 6
      service.nextStep();
      expect(service.currentStep()).toBe(6);
      expect(service.isStepComplete(5)).toBe(true);
    });

    it('supports backward navigation via prevStep() and goToStep()', () => {
      service.updateDefinition({ name: 'Test Template' });
      service.goToStep(4); // from step 1 with canProceed=true
      expect(service.currentStep()).toBe(4);

      service.prevStep();
      expect(service.currentStep()).toBe(3);

      service.goToStep(1);
      expect(service.currentStep()).toBe(1);
    });

    it('cancels creation, resets draft, and navigates to /migration/templates', () => {
      service.updateDefinition({ name: 'Draft Template' });
      service.cancel();
      expect(service.currentStep()).toBe(1);
      expect(service.draft().definition.name).toBe('');
      expect(routerMock.navigate).toHaveBeenCalledWith(['/migration/templates']);
    });
  });

  // =========================================================================
  // 2. STEP 1: DEFINITION & APPLICABILITY + STRICT M8 EXCLUSION
  // =========================================================================
  describe('2. Step 1: Definition & Applicability', () => {
    it('updates definition fields correctly', () => {
      service.updateDefinition({
        name: 'PostgreSQL to Snowflake Pipeline',
        description: 'Standard continuous replication',
        scope: 'WORKSPACE',
        sourceProvider: 'postgresql',
        targetProvider: 'snowflake',
        mode: 'M3_CDC'
      });

      const d = service.definition();
      expect(d.name).toBe('PostgreSQL to Snowflake Pipeline');
      expect(d.description).toBe('Standard continuous replication');
      expect(d.scope).toBe('WORKSPACE');
      expect(d.sourceProvider).toBe('postgresql');
      expect(d.targetProvider).toBe('snowflake');
      expect(d.mode).toBe('M3_CDC');
    });

    it('STRICT M8 EXCLUSION: ensures M8 (Validation Only) is never in template modes', () => {
      const allModeKeys = Object.keys(TEMPLATE_MODE_DESCRIPTORS);
      expect(allModeKeys).not.toContain('M8_VALIDATION_ONLY');
      expect(allModeKeys).not.toContain('M8');
      expect(allModeKeys).toEqual([
        'M1_BULK',
        'M2_BULK_CDC',
        'M3_CDC',
        'M4_INCREMENTAL',
        'M5_STATE_SYNC',
        'M6_SCHEMA_ONLY',
        'M7_DATA_ONLY'
      ]);
    });
  });

  // =========================================================================
  // 3. STEP 2: MIGRATION DEFAULTS & ZERO SECRETS
  // =========================================================================
  describe('3. Step 2: Migration Defaults', () => {
    it('updates naming pattern and execution priority', () => {
      service.updateDefaults({
        migrationNamePattern: 'CORP-{{PROJECT}}-{{ENV}}',
        executionPriority: 'CRITICAL',
        sourceConnectionPolicy: 'LOGICAL_TAG',
        sourceConnectionTag: 'oracle-prod',
        targetConnectionPolicy: 'LOGICAL_TAG',
        targetConnectionTag: 'snowflake-raw'
      });

      const md = service.migrationDefaults();
      expect(md.migrationNamePattern).toBe('CORP-{{PROJECT}}-{{ENV}}');
      expect(md.executionPriority).toBe('CRITICAL');
      expect(md.sourceConnectionPolicy).toBe('LOGICAL_TAG');
      expect(md.sourceConnectionTag).toBe('oracle-prod');
    });

    it('toggles required-at-use operator checklist items', () => {
      service.updateDefaults({
        requiredAtUse: {
          targetDatabaseRequired: true,
          scheduleRequired: true,
          secretBindingsRequired: true,
          workspaceSelectionRequired: false,
          notificationChannelsRequired: true
        }
      });

      const req = service.migrationDefaults().requiredAtUse;
      expect(req.scheduleRequired).toBe(true);
      expect(req.workspaceSelectionRequired).toBe(false);
      expect(req.notificationChannelsRequired).toBe(true);
    });
  });

  // =========================================================================
  // 4. STEP 3: SCOPE, MAPPING & DATA CONTROLS
  // =========================================================================
  describe('4. Step 3: Scope, Mapping & Data Controls', () => {
    it('manages object scope include/exclude rules', () => {
      const initialCount = service.scopeMapping().objectScopeRules.length;
      service.addScopeRule({
        ruleType: 'EXCLUDE',
        objectType: 'TABLE',
        pattern: 'audit_log_*',
        description: 'Exclude high-churn audit tables'
      });

      expect(service.scopeMapping().objectScopeRules.length).toBe(initialCount + 1);
      const added = service.scopeMapping().objectScopeRules[service.scopeMapping().objectScopeRules.length - 1];
      expect(added.pattern).toBe('audit_log_*');

      service.removeScopeRule(added.id);
      expect(service.scopeMapping().objectScopeRules.length).toBe(initialCount);
    });

    it('manages schema namespace mappings', () => {
      service.addSchemaMapping('sales_prod', 'sales_analytics');
      const mappings = service.scopeMapping().schemaMappings;
      const added = mappings.find(m => m.sourceSchema === 'sales_prod');
      expect(added).toBeDefined();
      expect(added?.targetSchema).toBe('sales_analytics');

      if (added) {
        service.removeSchemaMapping(added.id);
        expect(service.scopeMapping().schemaMappings.find(m => m.id === added.id)).toBeUndefined();
      }
    });

    it('manages column data type overrides', () => {
      service.addColumnTypeOverride('CLOB', 'TEXT');
      const overrides = service.scopeMapping().columnTypeOverrides;
      const added = overrides.find(o => o.sourceType === 'CLOB');
      expect(added?.targetType).toBe('TEXT');

      if (added) {
        service.removeColumnTypeOverride(added.id);
        expect(service.scopeMapping().columnTypeOverrides.find(o => o.id === added.id)).toBeUndefined();
      }
    });

    it('manages privacy masking rules and cleansing hygiene', () => {
      service.addMaskingRule('*credit_card*', 'HASH_SHA256', 'Hash PAN numbers');
      const rules = service.scopeMapping().maskingRules;
      const added = rules.find(r => r.targetPattern === '*credit_card*');
      expect(added?.maskingType).toBe('HASH_SHA256');

      service.updateScopeMapping({
        cleansing: {
          trimWhitespace: true,
          emptyStringToNull: false,
          deduplicateOnPrimaryKey: true
        }
      });
      expect(service.scopeMapping().cleansing.emptyStringToNull).toBe(false);
    });
  });

  // =========================================================================
  // 5. STEP 4: ENTERPRISE CONFIGURATION & DYNAMIC MODE ADAPTATION
  // =========================================================================
  describe('5. Step 4: Enterprise Configuration', () => {
    it('updates performance and checkpoint parameters', () => {
      service.updateEnterpriseConfig({
        performance: {
          extractThreads: 8,
          batchSize: 25000,
          bufferMemoryMb: 2048,
          maxThroughputMbps: 500
        },
        checkpointRecovery: {
          commitIntervalRows: 25000,
          commitIntervalSec: 60,
          retryCount: 5,
          errorHandlingPolicy: 'RETRY_EXPONENTIAL',
          maxSkippedErrors: 50
        }
      });

      const p = service.enterpriseConfig().performance;
      expect(p.extractThreads).toBe(8);
      expect(p.batchSize).toBe(25000);
      expect(p.maxThroughputMbps).toBe(500);

      const c = service.enterpriseConfig().checkpointRecovery;
      expect(c.retryCount).toBe(5);
      expect(c.errorHandlingPolicy).toBe('RETRY_EXPONENTIAL');
    });

    it('updates CDC configuration for M2/M3 modes', () => {
      service.updateEnterpriseConfig({
        cdcConfig: {
          cdcEngine: 'DEBEZIUM_STREAM',
          maxLagAlertSec: 120,
          heartbeatTracking: true,
          snapshotToStreamHandoff: 'QUIESCE_REQUIRED'
        }
      });

      const cdc = service.enterpriseConfig().cdcConfig;
      expect(cdc.cdcEngine).toBe('DEBEZIUM_STREAM');
      expect(cdc.maxLagAlertSec).toBe(120);
    });

    it('updates migration-side validation presets', () => {
      service.updateEnterpriseConfig({
        validationPresets: {
          rowCountReconciliation: true,
          schemaChecksumCheck: true,
          sampleDataHashRate: 'FULL_100_PCT'
        }
      });

      const v = service.enterpriseConfig().validationPresets;
      expect(v.sampleDataHashRate).toBe('FULL_100_PCT');
    });
  });

  // =========================================================================
  // 6. STEP 5: GOVERNANCE & REUSE RULES
  // =========================================================================
  describe('6. Step 5: Governance & Reuse Rules', () => {
    it('configures overridability and approval policies', () => {
      service.updateGovernance({
        overridability: {
          performanceSettings: 'LOCKED',
          mappingRules: 'REQUIRES_APPROVAL',
          scopeObjects: 'SUBSET_ONLY'
        },
        approvalAndPolicy: {
          requirePeerReview: true,
          enforceChangeFreezeWindow: true,
          auditLogLevel: 'COMPLIANCE'
        },
        secretReferenceRules: {
          vaultProvider: 'AWS_SECRETS_MANAGER',
          keyPathPrefix: 'corp/prod/migration/',
          guidanceNote: 'AWS IAM Role bound secrets only.'
        }
      });

      const g = service.governance();
      expect(g.overridability.performanceSettings).toBe('LOCKED');
      expect(g.approvalAndPolicy.requirePeerReview).toBe(true);
      expect(g.approvalAndPolicy.auditLogLevel).toBe('COMPLIANCE');
      expect(g.secretReferenceRules.vaultProvider).toBe('AWS_SECRETS_MANAGER');
      expect(g.secretReferenceRules.keyPathPrefix).toBe('corp/prod/migration/');
    });
  });

  // =========================================================================
  // 7. STEP 6: REVIEW & FINAL CREATION TRANSACTION
  // =========================================================================
  describe('7. Step 6: Review & Final Instantiation', () => {
    it('instantiates new template, prepends to inventory, and navigates home', () => {
      const initialInventoryCount = templatesService.templates().length;

      service.updateDefinition({
        name: 'Enterprise MySQL to PostgreSQL Migration Template',
        description: 'Automated CDC pipeline preset',
        scope: 'ORGANIZATION',
        sourceProvider: 'mysql',
        targetProvider: 'postgresql',
        mode: 'M2_BULK_CDC'
      });

      service.createTemplate();

      expect(templatesService.templates().length).toBe(initialInventoryCount + 1);
      const created = templatesService.templates()[0];
      expect(created.name).toBe('Enterprise MySQL to PostgreSQL Migration Template');
      expect(created.mode).toBe('M2_BULK_CDC');
      expect(created.applicability.sourceProviderName).toBe('MySQL');
      expect(created.applicability.targetProviderName).toBe('PostgreSQL');
      expect(created.scope).toBe('ORGANIZATION');
      expect(created.lifecycle).toBe('PUBLISHED');
      expect(created.usage.isUnused).toBe(true);
      expect(routerMock.navigate).toHaveBeenCalledWith(['/migration/templates']);
    });
  });
});
