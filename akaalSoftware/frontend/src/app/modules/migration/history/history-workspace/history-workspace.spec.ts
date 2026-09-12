import { describe, it, expect, beforeEach } from 'vitest';
import { HistoryWorkspaceService } from './history-workspace.service';
import { HISTORY_WORKSPACE_FIXTURES } from './history-workspace.fixtures';
import { HISTORY_FIXTURES } from '../history-home.fixtures';
import { HistoryWorkspaceTab } from './history-workspace.models';

describe('Migration History Workspace Suite', () => {
  let service: HistoryWorkspaceService;

  beforeEach(() => {
    service = new HistoryWorkspaceService();
  });

  describe('1. HistoryWorkspaceService Core State & Record Resolution', () => {
    it('should initialize with default active migration and overview tab in READY state', () => {
      expect(service.activeMigrationId()).toBe('mig-fin-core-01');
      expect(service.activeTab()).toBe('overview');
      expect(service.viewState()).toBe('READY');
      expect(service.errorMessage()).toBeNull();
      expect(service.currentRecord()).not.toBeNull();
    });

    it('should switch tabs accurately across all 10 destinations', () => {
      const allTabs: HistoryWorkspaceTab[] = [
        'overview',
        'timeline',
        'execution',
        'plan',
        'governance',
        'validation',
        'cutover',
        'recovery',
        'evidence',
        'audit'
      ];

      allTabs.forEach(tab => {
        service.setActiveTab(tab);
        expect(service.activeTab()).toBe(tab);
      });
    });

    it('should load directly mapped fixtures like mig-fin-core-01 and mig-audit-m8-01', () => {
      service.loadMigration('mig-fin-core-01');
      expect(service.viewState()).toBe('READY');
      const rec = service.currentRecord();
      expect(rec).not.toBeNull();
      expect(rec?.migrationId).toBe('mig-fin-core-01');
      expect(rec?.mode).toBe('M2_BULK_CDC');
      expect(rec?.cutover.isApplicableToMode).toBe(true);

      service.loadMigration('mig-audit-m8-01');
      expect(service.viewState()).toBe('READY');
      const m8Rec = service.currentRecord();
      expect(m8Rec).not.toBeNull();
      expect(m8Rec?.mode).toBe('M8_VALIDATION_ONLY');
      expect(m8Rec?.cutover.isApplicableToMode).toBe(false);
    });

    it('should dynamically generate rich workspace records for any home fixture (M1 to M8)', () => {
      const homeIds = ['mig-001', 'mig-002', 'mig-003', 'mig-004', 'mig-005', 'mig-006', 'mig-007', 'mig-008'];
      
      homeIds.forEach(id => {
        service.loadMigration(id);
        expect(service.viewState()).toBe('READY');
        const rec = service.currentRecord();
        expect(rec).not.toBeNull();
        expect(rec?.timeline.length).toBeGreaterThan(0);
        expect(rec?.executionRuns.length).toBeGreaterThan(0);
        expect(rec?.planAndConfig.sections.length).toBeGreaterThan(0);
        expect(rec?.evidence.artifacts.length).toBeGreaterThan(0);
        expect(rec?.auditTrail.length).toBeGreaterThan(0);
      });
    });

    it('should handle empty migration ID gracefully', () => {
      service.loadMigration('');
      expect(service.viewState()).toBe('EMPTY');
      expect(service.errorMessage()).toContain('No migration identifier provided');
    });
  });

  describe('2. Tab 2: Timeline Filtering & Event Projection', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should project all chronological timeline events by default', () => {
      const events = service.filteredTimelineEvents();
      expect(events.length).toBeGreaterThan(0);
    });

    it('should filter events by category', () => {
      service.setTimelineFilters('GOVERNANCE', 'ALL', '');
      const govEvents = service.filteredTimelineEvents();
      expect(govEvents.every(e => e.category === 'GOVERNANCE')).toBe(true);

      service.setTimelineFilters('VALIDATION', 'ALL', '');
      const valEvents = service.filteredTimelineEvents();
      expect(valEvents.every(e => e.category === 'VALIDATION')).toBe(true);
    });

    it('should filter events by severity', () => {
      service.setTimelineFilters('ALL', 'SUCCESS', '');
      const successEvents = service.filteredTimelineEvents();
      expect(successEvents.every(e => e.severity === 'SUCCESS')).toBe(true);
    });

    it('should search timeline descriptions and titles', () => {
      service.setTimelineFilters('ALL', 'ALL', 'Quorum');
      const searchEvents = service.filteredTimelineEvents();
      expect(searchEvents.length).toBeGreaterThan(0);
      expect(searchEvents.some(e => e.title.includes('Quorum') || e.description.includes('Quorum'))).toBe(true);
    });

    it('should reset timeline filters to defaults', () => {
      service.setTimelineFilters('PLANNING', 'INFO', 'xyz');
      service.resetTimelineFilters();
      expect(service.timelineCategory()).toBe('ALL');
      expect(service.timelineSeverity()).toBe('ALL');
      expect(service.timelineSearch()).toBe('');
    });
  });

  describe('3. Tab 3: Execution Run Selection & Telemetry', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should select execution runs and compute stages', () => {
      const rec = service.currentRecord();
      expect(rec?.executionRuns.length).toBeGreaterThan(0);
      
      const currentRun = service.currentExecutionRun();
      expect(currentRun).not.toBeNull();
      expect(currentRun?.stages.length).toBeGreaterThan(0);
      expect(currentRun?.attempts.length).toBeGreaterThan(0);
    });

    it('should allow switching between runs', () => {
      const rec = service.currentRecord();
      if (rec && rec.executionRuns.length > 1) {
        const secondRun = rec.executionRuns[1];
        service.selectExecutionRun(secondRun.runId);
        expect(service.currentExecutionRun()?.runId).toBe(secondRun.runId);
      }
    });
  });

  describe('4. Tab 4: Plan & Configuration Revision Diffing', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should expose plan SHA-256 fingerprint and config sections', () => {
      const rec = service.currentRecord();
      expect(rec?.planAndConfig.planFingerprint).toMatch(/^sha256:[a-f0-9]+/);
      expect(rec?.planAndConfig.sections.length).toBeGreaterThan(0);
    });

    it('should manage diff revision selectors', () => {
      service.setDiffRevisions(1, 3);
      expect(service.selectedDiffRevA()).toBe(1);
      expect(service.selectedDiffRevB()).toBe(3);
    });
  });

  describe('5. Tab 5: Governance & Multi-Approver Quorum', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should verify dual-control maker-checker quorum satisfaction', () => {
      const rec = service.currentRecord();
      expect(rec?.governance.length).toBeGreaterThan(0);
      const barrier = rec?.governance[0];
      expect(barrier?.makerCheckerSatisfied).toBe(true);
      expect(barrier?.quorumSatisfied).toBe(barrier?.quorumRequired);
      expect(barrier?.approvers.length).toBeGreaterThanOrEqual(2);
      expect(barrier?.planFingerprintBinding).toMatch(/^sha256:[a-f0-9]+/);
    });
  });

  describe('6. Tab 6: Validation & Reconciliation Discrepancies', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should compute validation runs, row counts, and Merkle tree root match', () => {
      const currentVal = service.currentValidationRun();
      expect(currentVal).not.toBeNull();
      expect(currentVal?.rowCountSource).toBeGreaterThan(0);
      expect(currentVal?.merkleTreeRootMatch).toBe(true);
    });

    it('should allow switching validation phases', () => {
      const rec = service.currentRecord();
      if (rec && rec.validationRuns.length > 1) {
        const secondVal = rec.validationRuns[1];
        service.selectValidationRun(secondVal.validationRunId);
        expect(service.currentValidationRun()?.validationRunId).toBe(secondVal.validationRunId);
      }
    });
  });

  describe('7. Tab 7: Cutover & Continuity Mode Awareness', () => {
    it('should declare cutover applicable for streaming mode M2', () => {
      service.loadMigration('mig-fin-core-01');
      const rec = service.currentRecord();
      expect(rec?.cutover.isApplicableToMode).toBe(true);
      expect(rec?.cutover.cutoverStatus).toBe('COMPLETED');
      expect(rec?.cutover.chronology.length).toBeGreaterThan(0);
      expect(rec?.cutover.downtimeSeconds).toBeDefined();
    });

    it('should declare cutover NOT applicable for assurance mode M8', () => {
      service.loadMigration('mig-audit-m8-01');
      const rec = service.currentRecord();
      expect(rec?.cutover.isApplicableToMode).toBe(false);
      expect(rec?.cutover.cutoverStatus).toBe('NOT_APPLICABLE');
    });
  });

  describe('8. Tab 8: Checkpoint Lineage & Recovery Posture', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should maintain fence epochs and non-duplicate safety attestations', () => {
      const rec = service.currentRecord();
      expect(rec?.recovery.fenceEpoch).toBeGreaterThanOrEqual(1);
      expect(rec?.recovery.dataSafetyAttestation.length).toBeGreaterThan(0);
    });
  });

  describe('9. Tab 9: Evidence Manifests & Execution Identity Seal', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should verify SHA-256 content digest and 15-field authoritative identity seal', () => {
      const rec = service.currentRecord();
      expect(rec?.evidence.integrity).toBe('SHA256_VERIFIED');
      expect(rec?.evidence.identitySeal.fields.length).toBeGreaterThan(0);
      expect(rec?.evidence.manifests.length).toBeGreaterThan(0);
      expect(rec?.evidence.artifacts.length).toBeGreaterThan(0);
    });
  });

  describe('10. Tab 10: Governed Audit Stream & Hash-Chain Integrity', () => {
    beforeEach(() => {
      service.loadMigration('mig-fin-core-01');
    });

    it('should project audit trail with immutable hash-chain links', () => {
      const audits = service.filteredAuditEvents();
      expect(audits.length).toBeGreaterThan(0);
      expect(audits.every(a => a.hashChainLinkSha256.startsWith('sha256:'))).toBe(true);
    });

    it('should filter audit events by actor and action', () => {
      const actors = service.auditDistinctActors();
      expect(actors.length).toBeGreaterThan(0);

      const targetActor = actors[0];
      service.setAuditFilters(targetActor, 'ALL', '');
      const filtered = service.filteredAuditEvents();
      expect(filtered.every(a => a.actorPrincipal === targetActor || a.actorRole === targetActor)).toBe(true);
    });

    it('should inspect audit event diff modal snapshot', () => {
      const audits = service.filteredAuditEvents();
      const first = audits[0];
      service.inspectAuditEvent(first);
      expect(service.activeAuditInspection()).toEqual(first);
      service.inspectAuditEvent(null);
      expect(service.activeAuditInspection()).toBeNull();
    });
  });
});
