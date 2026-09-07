import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ValidationResultsService } from './validation-results.service';
import { ValidationWorkstationService } from '../validation-workstation.service';

describe('ValidationResultsService (Workspace 4: Results & Evidence)', () => {
  let service: ValidationResultsService;
  let mockWorkstationService: Partial<ValidationWorkstationService>;

  beforeEach(() => {
    mockWorkstationService = {
      setActiveTab: vi.fn()
    };
    service = new ValidationResultsService();
    // Inject mock workstation service via property if needed
    (service as any).workstationService = mockWorkstationService;
    service.resetToDefault();
  });

  describe('1. Production Standby Baseline (Zero Fake Data Guarantee)', () => {
    it('should initialize strictly in truthful NOT_EVALUATED standby state', () => {
      expect(service.viewStatus()).toBe('NOT_EVALUATED');
      expect(service.isProductionDefault()).toBe(true);
      expect(service.verdict()).toBe('NOT_EVALUATED');
      expect(service.comparisonMode()).toBe('UNKNOWN');
      expect(service.temporalModel()).toBe('UNSPECIFIED');
      expect(service.executionState()).toBe('NOT_CONNECTED');
      expect(service.baselineState()).toBe('NOT_AVAILABLE');
      expect(service.evidence().evidenceAvailable).toBe(false);
      expect(service.remediationLineage().hasRemediationHistory).toBe(false);
      expect(service.runs()).toHaveLength(0);
      expect(service.auditTimeline()).toHaveLength(0);
      expect(service.artifacts().generationAvailable).toBe(false);
    });
  });

  describe('2. Independent Dimensions & Mandatory Combinations (Directive #1 & #2)', () => {
    it('should render PASSED + SYNC correctly without coupled state', () => {
      service.setFixture('PASSED_SYNC');
      expect(service.verdict()).toBe('PASSED');
      expect(service.comparisonMode()).toBe('SYNC');
      expect(service.temporalModel()).toBe('CONSISTENT_STATE');
      expect(service.unresolvedFindings()).toBeNull();
      expect(service.evidence().evidenceAvailable).toBe(true);
      expect(service.evidence().contentDigest).toMatch(/^sha256:/);
    });

    it('should render FAILED + SYNC correctly with unresolved findings', () => {
      service.setFixture('FAILED_SYNC');
      expect(service.verdict()).toBe('FAILED');
      expect(service.comparisonMode()).toBe('SYNC');
      expect(service.unresolvedFindings()?.totalCount).toBe(142);
      expect(service.unresolvedFindings()?.affectedObjectsCount).toBe(3);
      // Evidence available while validation failed is a valid, natural hostile state (Directive #30)
      expect(service.evidence().evidenceAvailable).toBe(true);
    });

    it('should render PASSED + ASYNC correctly without inferring failure', () => {
      service.setFixture('PASSED_ASYNC');
      expect(service.verdict()).toBe('PASSED');
      expect(service.comparisonMode()).toBe('ASYNC');
      expect(service.unresolvedFindings()).toBeNull();
    });

    it('should render FAILED + ASYNC correctly', () => {
      service.setFixture('FAILED_ASYNC');
      expect(service.verdict()).toBe('FAILED');
      expect(service.comparisonMode()).toBe('ASYNC');
      expect(service.unresolvedFindings()?.totalCount).toBe(8);
    });

    it('should render UNKNOWN comparison mode without guessing', () => {
      service.setFixture('UNKNOWN_RELATIONSHIP_MODE');
      expect(service.verdict()).toBe('PASSED');
      expect(service.comparisonMode()).toBe('UNKNOWN');
    });
  });

  describe('3. 4-Tier Assurance Framework Truth', () => {
    it('should present all 4 canonical assurance tiers', () => {
      service.setFixture('PASSED_SYNC');
      const tiers = service.assuranceTiers();
      expect(tiers).toHaveLength(4);
      expect(tiers[0].level).toBe('STRUCTURAL');
      expect(tiers[1].level).toBe('CARDINALITY');
      expect(tiers[2].level).toBe('PARTITION_FINGERPRINT');
      expect(tiers[3].level).toBe('COMPLETE_ATTRIBUTE');
      expect(tiers.every(t => t.status === 'PASSED')).toBe(true);
    });

    it('should accurately reflect failed assurance tiers when discrepancies occur', () => {
      service.setFixture('FAILED_SYNC');
      const tiers = service.assuranceTiers();
      expect(tiers[0].status).toBe('PASSED');
      expect(tiers[1].status).toBe('FAILED');
      expect(tiers[2].status).toBe('FAILED');
      expect(tiers[3].status).toBe('FAILED');
    });
  });

  describe('4. Navigation to Discrepancies Authority (Directive #18)', () => {
    it('should delegate navigation to parent workstation service', () => {
      service.navigateToDiscrepancies();
      expect(mockWorkstationService.setActiveTab).toHaveBeenCalledWith('discrepancies');
    });
  });

  describe('5. Immutable Remediation Lineage (Directive #11 & #29)', () => {
    it('should preserve immutable Initial Fail -> Repair -> Revalidation Pass lineage', () => {
      service.setFixture('REMEDIATED_REVALIDATED_PASSED');
      const lineage = service.remediationLineage();
      expect(lineage.hasRemediationHistory).toBe(true);
      // Initial validation remains FAILED (immutable!)
      expect(lineage.initialValidation?.verdict).toBe('FAILED');
      expect(lineage.initialValidation?.discrepancyCount).toBe(18);
      // Controlled repair completed
      expect(lineage.controlledRemediation?.status).toBe('COMPLETED');
      expect(lineage.controlledRemediation?.operationsCount).toBe(18);
      // Revalidation passed
      expect(lineage.revalidation?.verdict).toBe('PASSED');
      expect(lineage.revalidation?.remainingDiscrepancies).toBe(0);
    });

    it('should support Initial Fail -> Repair -> Revalidation Fail', () => {
      service.setFixture('REMEDIATED_REVALIDATION_FAILED');
      const lineage = service.remediationLineage();
      expect(lineage.hasRemediationHistory).toBe(true);
      expect(lineage.initialValidation?.verdict).toBe('FAILED');
      expect(lineage.revalidation?.verdict).toBe('FAILED');
      expect(lineage.revalidation?.remainingDiscrepancies).toBe(3);
    });
  });

  describe('6. Evidence & Integrity Record (Directive #6, #7, #8)', () => {
    it('should copy SHA-256 digest to clipboard', () => {
      service.setFixture('PASSED_SYNC');
      const mockClipboard = {
        writeText: vi.fn().mockResolvedValue(undefined)
      };
      (global as any).navigator.clipboard = mockClipboard;

      service.copyDigest();
      expect(mockClipboard.writeText).toHaveBeenCalledWith(service.evidence().contentDigest);
      expect(service.copiedDigest()).toBe(true);
    });

    it('should handle unavailable evidence gracefully', () => {
      service.resetToDefault();
      expect(service.evidence().evidenceAvailable).toBe(false);
    });
  });

  describe('7. Multi-Run History & Selection (Directive #19)', () => {
    it('should allow selecting historical runs', () => {
      service.setFixture('MULTIPLE_HISTORICAL_RUNS');
      expect(service.runs()).toHaveLength(5);
      expect(service.selectedRunId()).toBe('RUN-1080-05');

      service.selectRun('RUN-1080-03');
      expect(service.selectedRunId()).toBe('RUN-1080-03');
    });
  });

  describe('8. High-Volume Discrepancy Scale (Directive #28)', () => {
    it('should handle 40M aggregate findings gracefully', () => {
      service.setFixture('HIGH_VOLUME_40M_FINDINGS');
      expect(service.unresolvedFindings()?.totalCount).toBe(40000000);
      expect(service.unresolvedFindings()?.affectedObjectsCount).toBe(12);
    });
  });

  describe('9. Technical Drawer & Withheld States', () => {
    it('should toggle technical drawer visibility', () => {
      expect(service.isTechnicalDrawerOpen()).toBe(false);
      service.toggleTechnicalDrawer(true);
      expect(service.isTechnicalDrawerOpen()).toBe(true);
      service.toggleTechnicalDrawer(false);
      expect(service.isTechnicalDrawerOpen()).toBe(false);
    });

    it('should handle WITHHELD verdict correctly', () => {
      service.setFixture('WITHHELD');
      expect(service.viewStatus()).toBe('WITHHELD');
      expect(service.verdict()).toBe('WITHHELD');
    });

    it('should display truthful artifact notice on export attempt', () => {
      service.setFixture('PASSED_SYNC');
      service.triggerArtifactAction('Execution Summary Report');
      expect(service.actionNotice()).toContain('Export service integration pending');
    });
  });
});
