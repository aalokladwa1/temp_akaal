import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService, WizardDraftState } from '../../../../core/services/migration-ui.service';
import { Step7PlanAdapterService } from '../../../../core/services/step7-plan-adapter.service';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { Step8GovernanceAdapterService } from '../../../../core/services/step8-governance-adapter.service';
import { Step8GovernanceStoreService } from '../../../../core/services/step8-governance-store.service';
import { IpcService } from '../../../../core/services/ipc.service';
import { CanonicalPlanMode } from './step7-plan.models';
import {
  OverallReadinessStatus,
  ReadinessCheckCategory
} from './step8-governance.models';

describe('Step 8 — Governance & Readiness Master Architecture & Store Suite', () => {
  let ms: MigrationUiService;
  let step7Adapter: Step7PlanAdapterService;
  let step7Store: Step7PlanStoreService;
  let adapter: Step8GovernanceAdapterService;
  let ipc: IpcService;
  let store: Step8GovernanceStoreService;

  const createMockDraft = (
    mode: CanonicalPlanMode = 'M2_BULK_CDC',
    environment: 'Production' | 'Staging' | 'Development' = 'Production'
  ): WizardDraftState => ({
    ...ms.wizardDraft(),
    name: 'Oracle to Postgres Enterprise Migration',
    description: 'Production core banking ledger migration',
    mode,
    environment,
    sourceProvider: 'Oracle',
    sourceHost: 'orcl-prod.corp',
    sourcePort: 1521,
    sourceDatabase: 'ORCLPDB',
    sourceVerified: true,
    targetProvider: 'PostgreSQL',
    targetHost: 'pg-aurora.internal',
    targetPort: 5432,
    targetDatabase: 'finance',
    targetVerified: true,
    collisionPolicy: 'RENAME_AND_BACKUP',
    discoveryDepth: 'STANDARD',
    selectedTopologyNodes: ['schema-sct', 'tbl-cust', 'tbl-acc', 'tbl-tx'],
    scopeRules: [],
    activeStudioTab: 'MAPPING',
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
    currentStep: 8,
    completedSteps: new Set([1, 2, 3, 4, 5, 6, 7]),
    isDirty: false
  });

  beforeEach(() => {
    ms = new MigrationUiService();
    ms.resetWizardDraft();
    step7Adapter = new Step7PlanAdapterService();
    step7Store = new Step7PlanStoreService(ms, step7Adapter);
    adapter = new Step8GovernanceAdapterService();
    ipc = new IpcService();
    store = new Step8GovernanceStoreService(ms, step7Store, ipc, adapter);
  });

  describe('1. Overall Readiness State Evaluation', () => {
    it('evaluates to READY when all checks pass and all gates are approved or empty', () => {
      const draft = createMockDraft('M1_BULK', 'Development');
      ms.updateDraft(draft);

      const readiness = store.overallReadiness();
      expect(readiness.status).toBe('READY');
      expect(readiness.readinessSummary.blockedCount).toBe(0);
      expect(readiness.requiredActionCount).toBe(0);
    });

    it('evaluates to AWAITING_APPROVALS when gates exist and are pending sign-off', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      ms.updateDraft(draft);

      const gates = store.governanceGates();
      if (gates.length > 0) {
        expect(store.overallReadiness().status).toBe('AWAITING_APPROVALS');
        expect(store.canContinueToReview()).toBe(false);
      }
    });

    it('evaluates to ACTION_REQUIRED when source verification has blocking issues', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      draft.sourceVerified = false;
      draft.sourceVerificationResult = {
        ...(ms.wizardDraft().sourceVerificationResult || {}),
        fingerprint: 'mock-fp-blocked',
        isVerified: false,
        hasBlockingIssues: true
      } as any;
      ms.updateDraft(draft);

      const readiness = store.overallReadiness();
      expect(readiness.status).toBe('ACTION_REQUIRED');
      expect(readiness.readinessSummary.blockedCount).toBeGreaterThan(0);
      expect(store.canContinueToReview()).toBe(false);
    });
  });

  describe('2. Canonical Mode Mapping Across M1 through M7', () => {
    it('renders change capture category for M2_BULK_CDC mode', () => {
      const draft = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draft);

      const categories = store.readinessCategories();
      const hasCdc = categories.some(c => c.id === 'CHANGE_CAPTURE');
      expect(hasCdc).toBe(true);
    });

    it('omits change capture category for M1_BULK mode', () => {
      const draft = createMockDraft('M1_BULK');
      ms.updateDraft(draft);

      const categories = store.readinessCategories();
      const hasCdc = categories.some(c => c.id === 'CHANGE_CAPTURE');
      expect(hasCdc).toBe(false);
    });

    it('omits storage volume checks for M6_SCHEMA_ONLY mode', () => {
      const draft = createMockDraft('M6_SCHEMA_ONLY');
      ms.updateDraft(draft);

      const categories = store.readinessCategories();
      const hasCapacity = categories.some(c => c.id === 'CAPACITY_RESOURCES');
      expect(hasCapacity).toBe(false);
    });

    it('includes DDL and bulk checks for M7_DATA_ONLY mode', () => {
      const draft = createMockDraft('M7_DATA_ONLY');
      ms.updateDraft(draft);

      const categories = store.readinessCategories();
      const hasConnections = categories.some(c => c.id === 'CONNECTIONS_ACCESS');
      const hasExecution = categories.some(c => c.id === 'EXECUTION_REQUIREMENTS');
      expect(hasConnections).toBe(true);
      expect(hasExecution).toBe(true);
    });
  });

  describe('3. Governance Gate Sign-off & Separation of Duties', () => {
    it('approves a gate and updates reactive state and eligibility', async () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      ms.updateDraft(draft);

      const gates = store.governanceGates();
      if (gates.length > 0) {
        const gateId = gates[0].id;
        expect(gates[0].status).toBe('PENDING_APPROVAL');

        await store.approveGate(gateId, 'Approved by lead DBA');

        const updatedGates = store.governanceGates();
        const updatedGate = updatedGates.find(g => g.id === gateId);
        expect(updatedGate?.status).toBe('APPROVED');
        expect(updatedGate?.decisionComment).toBe('Approved by lead DBA');
      }
    });

    it('rejects a gate and marks overall readiness as ACTION_REQUIRED', async () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      ms.updateDraft(draft);

      const gates = store.governanceGates();
      if (gates.length > 0) {
        const gateId = gates[0].id;
        await store.rejectGate(gateId, 'High CDC lag detected in source');

        const updatedGates = store.governanceGates();
        const updatedGate = updatedGates.find(g => g.id === gateId);
        expect(updatedGate?.status).toBe('REJECTED');
        expect(store.overallReadiness().status).toBe('ACTION_REQUIRED');
        expect(store.canContinueToReview()).toBe(false);
      }
    });
  });

  describe('4. Policy Acknowledgements Flow', () => {
    it('generates high-concurrency acknowledgement in production when workers > 8', async () => {
      const draft = createMockDraft('M1_BULK', 'Production');
      draft.basicView = {
        ...draft.basicView!,
        derivedMaxWorkers: 16
      };
      ms.updateDraft(draft);

      const acks = store.policyAcknowledgements();
      expect(acks.length).toBeGreaterThan(0);
      expect(acks[0].id).toBe('ack-high-concurrency');
      expect(acks[0].isAcknowledged).toBe(false);

      await store.recordAcknowledgement(acks[0].id, 'Production capacity verified with network team');

      const updatedAcks = store.policyAcknowledgements();
      expect(updatedAcks[0].isAcknowledged).toBe(true);
      expect(updatedAcks[0].rationale).toBe('Production capacity verified with network team');
    });
  });

  describe('5. Drawer & Modal UI State Management', () => {
    it('toggles approval drawer open and closed', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      ms.updateDraft(draft);

      const gates = store.governanceGates();
      if (gates.length > 0) {
        store.openApprovalDrawer(gates[0]);
        expect(store.selectedApprovalGate()?.id).toBe(gates[0].id);

        store.closeApprovalDrawer();
        expect(store.selectedApprovalGate()).toBeNull();
      }
    });

    it('toggles readiness check inspector drawer open and closed', () => {
      const draft = createMockDraft('M1_BULK');
      ms.updateDraft(draft);

      const checks = store.readinessCategories()[0].checks;
      store.openReadinessDrawer(checks[0]);
      expect(store.selectedReadinessCheck()?.id).toBe(checks[0].id);

      store.closeReadinessDrawer();
      expect(store.selectedReadinessCheck()).toBeNull();
    });

    it('toggles technical details modal open and closed', () => {
      store.openTechnicalModal();
      expect(store.isTechnicalModalOpen()).toBe(true);

      store.closeTechnicalModal();
      expect(store.isTechnicalModalOpen()).toBe(false);
    });

    it('toggles activity drawer open and closed', () => {
      store.openActivityDrawer();
      expect(store.isActivityDrawerOpen()).toBe(true);

      store.closeActivityDrawer();
      expect(store.isActivityDrawerOpen()).toBe(false);
    });
  });

  describe('6. Upstream Remediation Routing', () => {
    it('navigates to upstream step when requested', () => {
      store.routeToUpstreamStep(2);
      expect(ms.wizardDraft().currentStep).toBe(2);

      store.routeToUpstreamStep(6);
      expect(ms.wizardDraft().currentStep).toBe(6);
    });
  });
});
