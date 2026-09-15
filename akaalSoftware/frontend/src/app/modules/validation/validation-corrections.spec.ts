import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationRepairService } from './workstation/repair/validation-repair.service';
import { ValidationResultsService } from './workstation/results/validation-results.service';
import { ValidationHomeService } from '../../core/services/validation-home.service';
import { ValidationUiService } from '../../core/services/validation-ui.service';
import { ALL_PROVIDER_SCHEMAS } from '../../core/models/provider-form-schemas';
import { Step2SourceComponent } from './create/steps/step2-source.component';
import { Step3TargetComponent } from './create/steps/step3-target.component';

describe('DevKros Validation CHECK1 Part 2.5 — Mandatory Corrections Regression', () => {
  describe('B-VAL-01: Truthful Governed Operations (No Fake Signatures / IDs)', () => {
    let repairService: ValidationRepairService;

    beforeEach(() => {
      repairService = new ValidationRepairService();
    });

    it('should fail closed on approveProposal without backend execution connection', () => {
      repairService.setFixture('SENSITIVE_DATA_TRANSFORMATION');
      repairService.approveProposal('Security Officer 2 / Compliance Lead');
      
      expect(repairService.errorMessage()).toContain('Live sign-off & cryptographic signature requires backend connection (CHECK2)');
      const gov = repairService.governance();
      expect(gov?.authorizationNote).toContain('requires backend connection');
    });

    it('should fail closed on executeRepair without backend connection', () => {
      repairService.setFixture('SENSITIVE_DATA_TRANSFORMATION');
      repairService.executeRepair();
      
      expect(repairService.errorMessage()).toContain('Live repair execution requires backend connection (CHECK2)');
    });

    it('should fail closed on triggerRevalidation without backend connection', () => {
      repairService.setFixture('SENSITIVE_DATA_TRANSFORMATION');
      repairService.triggerRevalidation();
      
      expect(repairService.errorMessage()).toContain('Live revalidation scan requires backend connection (CHECK2)');
    });
  });

  describe('B-VAL-02: Truthful Results & Evidence (No Synthetic Fixture Fallback)', () => {
    let resultsService: ValidationResultsService;

    beforeEach(() => {
      resultsService = new ValidationResultsService();
    });

    it('should default strictly to truthful NOT_EVALUATED / NOT_CONNECTED state without synthetic data', () => {
      resultsService.resetToDefault();
      const state = resultsService.state();

      expect(state.verdict).toBe('NOT_EVALUATED');
      expect(state.executionState).toBe('NOT_CONNECTED');
      expect(state.evidence.evidenceAvailable).toBe(false);
      expect(state.evidence.integrityNote).toContain('has not been generated');
    });
  });

  describe('Validation Home Baseline State Truth', () => {
    let homeService: ValidationHomeService;

    beforeEach(() => {
      homeService = new ValidationHomeService();
    });

    it('should initialize loadBaselineState with truthful empty arrays when backend is disconnected', () => {
      homeService.loadBaselineState();

      expect(homeService.validations().length).toBe(0);
      expect(homeService.attentionItems().length).toBe(0);
      expect(homeService.upcomingValidations().length).toBe(0);
      expect(homeService.recentResults().length).toBe(0);
      expect(homeService.activities().length).toBe(0);
      expect(homeService.summary()).toBeNull();
    });
  });

  describe('Provider Authority Truth & Schemas', () => {
    it('should expose canonical provider schemas without relying on superseded ALL_48_PROVIDER_SCHEMAS alias', () => {
      expect(ALL_PROVIDER_SCHEMAS['SQLite']).toBeTruthy();
      expect(ALL_PROVIDER_SCHEMAS['Oracle Database']).toBeTruthy();
      expect(ALL_PROVIDER_SCHEMAS['OCI Object Storage']).toBeTruthy();
    });
  });

  describe('Validation Draft Defaults', () => {
    let uiService: ValidationUiService;

    beforeEach(() => {
      uiService = new ValidationUiService();
    });

    it('should not contain hardcoded user/operator defaults', () => {
      const draft = uiService.newValidationDraft();
      expect(draft.owner).toBeUndefined();
    });
  });

  describe('C-VAL-RES-02: Source & Target Provider Role Filtering & Derived Counts', () => {
    let uiService: ValidationUiService;
    let step2: Step2SourceComponent;
    let step3: Step3TargetComponent;

    beforeEach(() => {
      uiService = new ValidationUiService();
      step2 = new Step2SourceComponent(uiService);
      step3 = new Step3TargetComponent(uiService);
    });

    it('should correctly include BOTH-role relational provider in Step 2 Source and Step 3 Target', () => {
      const postgresSource = step2.catalogEngines.find(e => e.name === 'PostgreSQL');
      const postgresTarget = step3.catalogEngines.find(e => e.name === 'PostgreSQL');

      expect(postgresSource).toBeDefined();
      expect(postgresTarget).toBeDefined();
    });

    it('should include SOURCE_ONLY provider (Salesforce) in Step 2 Source but exclude it from Step 3 Target', () => {
      const sfSource = step2.catalogEngines.find(e => e.name === 'Salesforce');
      const sfTarget = step3.catalogEngines.find(e => e.name === 'Salesforce');

      expect(sfSource).toBeDefined();
      expect(sfTarget).toBeUndefined();
    });

    it('should correctly include special surfaces (File Dataset, Managed Cloud, Streaming, Object Storage) in Step 2 and Step 3', () => {
      // File Dataset
      expect(step2.catalogEngines.find(e => e.name === 'File Dataset')).toBeDefined();
      expect(step3.catalogEngines.find(e => e.name === 'File Dataset')).toBeDefined();

      // Managed Cloud
      expect(step2.catalogEngines.find(e => e.name === 'AWS Managed Cloud')).toBeDefined();
      expect(step3.catalogEngines.find(e => e.name === 'AWS Managed Cloud')).toBeDefined();

      // Streaming (Kafka)
      expect(step2.catalogEngines.find(e => e.name === 'Apache Kafka')).toBeDefined();
      expect(step3.catalogEngines.find(e => e.name === 'Apache Kafka')).toBeDefined();

      // Object Storage (S3)
      expect(step2.catalogEngines.find(e => e.name === 'Amazon S3')).toBeDefined();
      expect(step3.catalogEngines.find(e => e.name === 'Amazon S3')).toBeDefined();
    });

    it('should derive accurate role-filtered family counts for Step 2 (54 total, 3 apps) and Step 3 (53 total, 2 apps)', () => {
      // Step 2 Source: 54 total, Enterprise Applications = 3
      const s2AllTab = step2.catalogTabs.find(t => t.id === 'ALL');
      const s2AppTab = step2.catalogTabs.find(t => t.id === 'ENTERPRISE_APPLICATIONS');
      expect(s2AllTab?.count).toBe(54);
      expect(s2AppTab?.count).toBe(3);

      // Step 3 Target: 53 total, Enterprise Applications = 2 (Salesforce excluded)
      const s3AllTab = step3.catalogTabs.find(t => t.id === 'ALL');
      const s3AppTab = step3.catalogTabs.find(t => t.id === 'ENTERPRISE_APPLICATIONS');
      expect(s3AllTab?.count).toBe(53);
      expect(s3AppTab?.count).toBe(2);
    });
  });
});
