import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationRepairService } from './workstation/repair/validation-repair.service';
import { ValidationResultsService } from './workstation/results/validation-results.service';
import { ValidationHomeService } from '../../core/services/validation-home.service';
import { ValidationUiService } from '../../core/services/validation-ui.service';
import { ALL_PROVIDER_SCHEMAS } from '../../core/models/provider-form-schemas';

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
});
