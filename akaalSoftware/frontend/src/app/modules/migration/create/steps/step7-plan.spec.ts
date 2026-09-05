import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService, WizardDraftState } from '../../../../core/services/migration-ui.service';
import { Step7PlanAdapterService } from '../../../../core/services/step7-plan-adapter.service';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { CanonicalPlanMode, PlanDagNode, NewGateDraft, ApprovalBarrierConfig } from './step7-plan.models';

describe('Step 7 — Dynamic Migration Plan Master Architecture & Store Suite', () => {
  let ms: MigrationUiService;
  let adapter: Step7PlanAdapterService;
  let store: Step7PlanStoreService;

  const createMockDraft = (mode: CanonicalPlanMode, environment: 'Production' | 'Staging' | 'Development' = 'Production'): WizardDraftState => ({
    ...ms.wizardDraft(),
    name: 'Oracle to Postgres Enterprise Migration',
    description: 'Production core banking ledger migration',
    mode,
    environment,
    sourceProvider: 'Oracle',
    sourceHost: 'orcl-prod.corp',
    sourcePort: 1521,
    sourceDatabase: 'ORCLPDB',
    targetProvider: 'PostgreSQL',
    targetHost: 'pg-aurora.internal',
    targetPort: 5432,
    targetDatabase: 'finance',
    collisionPolicy: 'RENAME_AND_BACKUP',
    discoveryDepth: 'STANDARD',
    selectedTopologyNodes: ['schema-sct', 'tbl-cust', 'tbl-acc', 'tbl-tx'],
    scopeRules: [],
    activeStudioTab: 'MAPPING',
    isAdvancedConfigMode: false,
    basicView: {
      performancePreset: 'BALANCED',
      derivedMinWorkers: 2,
      derivedMaxWorkers: 16,
      derivedBatchMb: 32,
      durabilityLevel: 'STANDARD',
      spillHeadroomGb: 16,
      cdcLagObjectiveMs: 500,
      watermarkFreshnessSec: 60,
      validationDepth: 'STANDARD'
    },
    configOverrides: {},
    hasInvalidatedConfig: false,
    planStale: false,
    planVersion: 1,
    customBarriersCount: 0,
    readinessPassed: true,
    requiresQuorumApproval: false,
    scheduleChoice: 'RUN_NOW',
    currentStep: 7,
    completedSteps: new Set([1, 2, 3, 4, 5, 6]),
    isDirty: false
  });

  beforeEach(() => {
    ms = new MigrationUiService();
    ms.resetWizardDraft();
    adapter = new Step7PlanAdapterService();
    store = new Step7PlanStoreService(ms, adapter);
  });

  describe('1. Plan Adapter Service — Canonical Modes (M1–M7)', () => {
    it('should generate valid M1_BULK execution plan', () => {
      const draft = createMockDraft('M1_BULK', 'Staging');
      const plan = adapter.buildPlanDescriptor(draft);

      expect(plan.mode).toBe('M1_BULK');
      expect(plan.nodes.length).toBeGreaterThanOrEqual(6);
      expect(plan.nodes[0].stageType).toBe('PRE_FLIGHT');
      expect(plan.nodes.some(n => n.stageType === 'BULK_LOAD' || n.stageType === 'BULK_EXTRACT')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'INDEX_REBUILD')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'POST_VALIDATION')).toBe(true);
      expect(plan.summary.scope.totalObjects).toBe(303);
    });

    it('should generate valid M2_BULK_CDC execution plan with mandatory production barrier', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      const plan = adapter.buildPlanDescriptor(draft);

      expect(plan.mode).toBe('M2_BULK_CDC');
      expect(plan.nodes.some(n => n.stageType === 'CDC_CAPTURE')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'BULK_EXTRACT')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'CDC_APPLY')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'STATE_COMPARE')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'CUTOVER')).toBe(true);

      // Verify mandatory production barrier
      const barrier = plan.nodes.find(n => n.nodeType === 'APPROVAL_BARRIER');
      expect(barrier).toBeDefined();
      expect(barrier?.isMandatoryBarrier).toBe(true);
      expect(barrier?.policyLocked).toBe(true);
      expect(barrier?.barrierConfig?.signerPolicy).toBe('FOUR_EYES');
      expect(barrier?.barrierConfig?.separationOfDuties).toBe(true);
    });

    it('should generate valid M3_CDC continuous streaming plan', () => {
      const draft = createMockDraft('M3_CDC', 'Development');
      const plan = adapter.buildPlanDescriptor(draft);

      expect(plan.mode).toBe('M3_CDC');
      expect(plan.nodes.some(n => n.stageType === 'CDC_CAPTURE')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'CDC_APPLY')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'STATE_COMPARE')).toBe(true);
    });

    it('should generate valid M4_INCREMENTAL watermark scan plan', () => {
      const draft = createMockDraft('M4_INCREMENTAL', 'Staging');
      const plan = adapter.buildPlanDescriptor(draft);

      expect(plan.mode).toBe('M4_INCREMENTAL');
      expect(plan.nodes.some(n => n.stageType === 'DATA_PREPARATION')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'BULK_LOAD')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'POST_VALIDATION')).toBe(true);
    });

    it('should generate valid M5_STATE_SYNC comparison and delta reconcile plan', () => {
      const draft = createMockDraft('M5_STATE_SYNC', 'Staging');
      const plan = adapter.buildPlanDescriptor(draft);

      expect(plan.mode).toBe('M5_STATE_SYNC');
      expect(plan.nodes.some(n => n.stageType === 'STATE_COMPARE')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'DATA_PREPARATION')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'BULK_LOAD')).toBe(true);
    });

    it('should generate valid M6_SCHEMA_ONLY DDL and transpiled objects plan', () => {
      const draft = createMockDraft('M6_SCHEMA_ONLY', 'Staging');
      const plan = adapter.buildPlanDescriptor(draft);

      expect(plan.mode).toBe('M6_SCHEMA_ONLY');
      expect(plan.nodes.some(n => n.stageType === 'SCHEMA_DDL')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'INDEX_REBUILD')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'POST_VALIDATION')).toBe(true);
    });

    it('should generate valid M7_DATA_ONLY pure table data ingestion plan', () => {
      const draft = createMockDraft('M7_DATA_ONLY', 'Staging');
      const plan = adapter.buildPlanDescriptor(draft);

      expect(plan.mode).toBe('M7_DATA_ONLY');
      expect(plan.nodes.some(n => n.stageType === 'BULK_EXTRACT')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'INDEX_REBUILD')).toBe(true);
      expect(plan.nodes.some(n => n.stageType === 'POST_VALIDATION')).toBe(true);
    });

    it('should compute deterministic SHA-256 fingerprint for plan descriptor', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      const plan1 = adapter.buildPlanDescriptor(draft);
      const plan2 = adapter.buildPlanDescriptor(draft);

      expect(plan1.fingerprint).toBe(plan2.fingerprint);
      expect(plan1.fingerprint.startsWith('sha256:')).toBe(true);
    });

    it('should include provenance indicators on work objects', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      const plan = adapter.buildPlanDescriptor(draft);
      const bulkStage = plan.nodes.find(n => n.stageType === 'BULK_EXTRACT');

      expect(bulkStage?.workObjects).toBeDefined();
      expect(bulkStage?.workObjects?.length).toBeGreaterThan(0);
      const firstObj = bulkStage!.workObjects![0];
      expect(firstObj.rowsProvenance).toBe('EXACT');
      expect(firstObj.sizeProvenance).toBe('ESTIMATED');
    });
  });

  describe('2. Plan Store Service — State & Interaction Signals', () => {
    beforeEach(() => {
      ms.updateDraft({
        mode: 'M2_BULK_CDC',
        environment: 'Production',
        currentStep: 7
      });
    });

    it('should initialize with valid activePlan and computed projections', () => {
      expect(store.activePlan()).toBeDefined();
      expect(store.nodes().length).toBeGreaterThan(0);
      expect(store.edges().length).toBeGreaterThan(0);
      expect(store.isStep7Valid()).toBe(true);
      expect(store.summary().scope.totalObjects).toBe(303);
      expect(store.technicalDetails().canonicalFingerprint).toBeDefined();
    });

    it('should open and close stage drawer', () => {
      const firstStage = store.executionStages()[0];
      store.openStageDrawer(firstStage);

      expect(store.selectedStage()?.id).toBe(firstStage.id);
      expect(store.selectedGate()).toBeNull();

      store.closeStageDrawer();
      expect(store.selectedStage()).toBeNull();
    });

    it('should open and close approval gate drawer', () => {
      const firstGate = store.approvalGates()[0];
      expect(firstGate).toBeDefined();

      store.openGateDrawer(firstGate);
      expect(store.selectedGate()?.id).toBe(firstGate.id);
      expect(store.selectedStage()).toBeNull();

      store.closeGateDrawer();
      expect(store.selectedGate()).toBeNull();
    });

    it('should open and close add gate modal with eligible edges', () => {
      expect(store.eligibleEdges().length).toBeGreaterThan(0);

      store.openAddGateModal(store.eligibleEdges()[0].id);
      expect(store.isAddGateModalOpen()).toBe(true);
      expect(store.selectedPlacementEdgeId()).toBe(store.eligibleEdges()[0].id);

      store.closeAddGateModal();
      expect(store.isAddGateModalOpen()).toBe(false);
    });

    it('should open and close technical details modal', () => {
      store.openTechnicalModal();
      expect(store.isTechnicalModalOpen()).toBe(true);

      store.closeTechnicalModal();
      expect(store.isTechnicalModalOpen()).toBe(false);
    });

    it('should support adding and removing custom approval gates', () => {
      const eligibleEdge = store.eligibleEdges()[0];
      expect(eligibleEdge).toBeDefined();

      const initialGateCount = store.approvalGates().length;
      const draft: NewGateDraft = {
        placementEdgeId: eligibleEdge.id,
        gateName: 'Pre-Load Custom Gate',
        description: 'Operator verification check',
        protectedOperation: 'Bulk Parallel Transfer',
        signerPolicy: 'FOUR_EYES',
        requiredSignatures: 2,
        cdcMaxLagMs: 1000,
        requireDlqEmpty: true,
        requireCheckpointClean: true,
        requireValidationPass: true,
        requireTargetTablesEmpty: false,
        timeoutMinutes: 60,
        timeoutAction: 'ALERT_AND_HOLD',
        rejectionAction: 'HALT_MIGRATION'
      };

      store.addApprovalGate(draft);

      expect(store.approvalGates().length).toBe(initialGateCount + 1);
      const added = store.approvalGates().find(g => g.gateName === 'Pre-Load Custom Gate');
      expect(added).toBeDefined();
      expect(added?.isMandatory).toBe(false);

      // Remove the custom gate
      store.removeApprovalGate(added!.id);
      expect(store.approvalGates().length).toBe(initialGateCount);
    });

    it('should update custom approval gate parameters', () => {
      const eligibleEdge = store.eligibleEdges()[0];
      store.addApprovalGate({
        placementEdgeId: eligibleEdge.id,
        gateName: 'Original Gate Name',
        description: 'Original description',
        protectedOperation: 'Bulk Transfer',
        signerPolicy: 'SOLE_OWNER',
        requiredSignatures: 1,
        cdcMaxLagMs: 5000,
        requireDlqEmpty: true,
        requireCheckpointClean: true,
        requireValidationPass: false,
        requireTargetTablesEmpty: false,
        timeoutMinutes: 30,
        timeoutAction: 'AUTO_REJECT',
        rejectionAction: 'FAIL_FAST'
      });

      const gate = store.approvalGates().find(g => g.gateName === 'Original Gate Name')!;
      expect(gate).toBeDefined();

      store.updateApprovalGate({
        ...gate,
        gateName: 'Updated Gate Name',
        requiredSignatures: 2
      });

      const updated = store.approvalGates().find(g => g.id === gate.id);
      expect(updated?.gateName).toBe('Updated Gate Name');
      expect(updated?.requiredSignatures).toBe(2);
    });

    it('should toggle issue risk acknowledgement', () => {
      const firstIssue = store.issues()[0];
      expect(firstIssue).toBeDefined();

      expect(store.acknowledgedIssueIds().has(firstIssue.id)).toBe(false);
      store.toggleAcknowledgeIssue(firstIssue.id);
      expect(store.acknowledgedIssueIds().has(firstIssue.id)).toBe(true);

      store.toggleAcknowledgeIssue(firstIssue.id);
      expect(store.acknowledgedIssueIds().has(firstIssue.id)).toBe(false);
    });

    it('should toggle visible advisories limit', () => {
      expect(store.showAllAdvisories()).toBe(false);
      store.toggleShowAllAdvisories();
      expect(store.showAllAdvisories()).toBe(true);
    });
  });
});
