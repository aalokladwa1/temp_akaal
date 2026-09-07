// ============================================================================
// AKAAL CREATE MIGRATION — STEP 9: REVIEW, SCHEDULE & INITIALIZE
// MASTER UNIT TEST SUITE (VITEST)
// ============================================================================

import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MigrationUiService, WizardDraftState } from '../../../../core/services/migration-ui.service';
import { Step7PlanAdapterService } from '../../../../core/services/step7-plan-adapter.service';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { Step8GovernanceAdapterService } from '../../../../core/services/step8-governance-adapter.service';
import { Step8GovernanceStoreService } from '../../../../core/services/step8-governance-store.service';
import { Step9ReviewAdapterService } from '../../../../core/services/step9-review-adapter.service';
import { Step9ReviewStoreService } from '../../../../core/services/step9-review-store.service';
import { IpcService } from '../../../../core/services/ipc.service';
import { CanonicalPlanMode } from './step7-plan.models';

describe('Step 9 — Review, Schedule & Initialize Master Test Suite', () => {
  let ms: MigrationUiService;
  let step7Adapter: Step7PlanAdapterService;
  let step7Store: Step7PlanStoreService;
  let step8Adapter: Step8GovernanceAdapterService;
  let step8Store: Step8GovernanceStoreService;
  let adapter: Step9ReviewAdapterService;
  let ipc: IpcService;
  let store: Step9ReviewStoreService;
  let mockRouter: any;

  const createMockDraft = (
    mode: CanonicalPlanMode = 'M2_BULK_CDC',
    environment: 'Production' | 'Staging' | 'Development' = 'Production'
  ): WizardDraftState => ({
    ...ms.wizardDraft(),
    name: 'Oracle to Aurora Postgres Migration',
    description: 'Core banking ledger database migration',
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
    collisionPolicy: 'FAIL_ON_COLLISION',
    discoveryDepth: 'STANDARD',
    selectedTopologyNodes: ['schema-sct', 'tbl-cust', 'tbl-acc', 'tbl-tx'],
    scopeRules: [],
    activeStudioTab: 'MAPPING',
    basicView: {
      performancePreset: 'BALANCED',
      derivedMinWorkers: 4,
      derivedMaxWorkers: 16,
      derivedBatchMb: 32,
      durabilityLevel: 'STANDARD',
      spillHeadroomGb: 16,
      cdcLagObjectiveMs: 500,
      watermarkFreshnessSec: 60,
      validationDepth: 'STANDARD'
    },
    currentStep: 9,
    completedSteps: new Set([1, 2, 3, 4, 5, 6, 7, 8]),
    isDirty: false
  });

  beforeEach(() => {
    ms = new MigrationUiService();
    ms.resetWizardDraft();
    step7Adapter = new Step7PlanAdapterService();
    step7Store = new Step7PlanStoreService(ms, step7Adapter);
    step8Adapter = new Step8GovernanceAdapterService();
    step8Store = new Step8GovernanceStoreService(ms, step7Store, new IpcService(), step8Adapter);
    adapter = new Step9ReviewAdapterService();
    ipc = new IpcService();
    mockRouter = {
      navigate: vi.fn()
    };
    store = new Step9ReviewStoreService(ms, step7Store, step8Store, ipc, adapter, mockRouter);
  });

  // --------------------------------------------------------------------------
  // 1. PRESENTATION & IDENTITY ADAPTATION
  // --------------------------------------------------------------------------
  describe('1. Migration Identity & Route Adaptation', () => {
    it('adapts canonical migration identity from creation draft', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      ms.updateDraft(draft);

      const identity = store.migrationIdentity();
      expect(identity.migrationName).toBe('Oracle to Aurora Postgres Migration');
      expect(identity.environment).toBe('Production');
      expect(identity.mode).toBe('M2_BULK_CDC');
      expect(identity.modeTitle).toContain('Bulk Migration + Continuous CDC');
      expect(identity.source.provider).toBe('Oracle');
      expect(identity.target.provider).toBe('PostgreSQL');
      expect(identity.migrationId).toBeTruthy();
      expect(identity.planFingerprint).toBeTruthy();
    });

    it('adapts route labels truthfully with source and target database instances', () => {
      const draft = createMockDraft('M1_BULK', 'Development');
      ms.updateDraft(draft);

      const identity = store.migrationIdentity();
      expect(identity.source.label).toContain('ORCLPDB');
      expect(identity.target.label).toContain('finance');
    });
  });

  // --------------------------------------------------------------------------
  // 2. MIGRATION REVIEW GROUPS (5 DOCUMENT SECTIONS)
  // --------------------------------------------------------------------------
  describe('2. Migration Review 5-Group Document Structure', () => {
    it('generates 5 distinct review groups with upstream remediation routes', () => {
      const draft = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draft);

      const groups = store.reviewGroups();
      expect(groups.length).toBe(5);

      const ids = groups.map(g => g.id);
      expect(ids).toEqual(['SCOPE_DATA', 'DATA_CONTROLS', 'EXECUTION', 'PLAN', 'GOVERNANCE_READINESS']);

      // Check upstream step targets
      expect(groups.find(g => g.id === 'SCOPE_DATA')?.upstreamStep).toBe(4);
      expect(groups.find(g => g.id === 'DATA_CONTROLS')?.upstreamStep).toBe(5);
      expect(groups.find(g => g.id === 'EXECUTION')?.upstreamStep).toBe(6);
      expect(groups.find(g => g.id === 'PLAN')?.upstreamStep).toBe(7);
      expect(groups.find(g => g.id === 'GOVERNANCE_READINESS')?.upstreamStep).toBe(8);
    });

    it('adapts mode-specific metadata for M6_SCHEMA_ONLY', () => {
      const draft = createMockDraft('M6_SCHEMA_ONLY');
      ms.updateDraft(draft);

      const groups = store.reviewGroups();
      const scopeGroup = groups.find(g => g.id === 'SCOPE_DATA');
      expect(scopeGroup?.fields.some(f => f.value.includes('Metadata Only'))).toBe(true);
    });
  });

  // --------------------------------------------------------------------------
  // 3. BEFORE YOU START (DECISION-QUALITY INTELLIGENCE)
  // --------------------------------------------------------------------------
  describe('3. Decision-Quality Intelligence Adaptation', () => {
    it('provides data scale with measured evidence classification', () => {
      const draft = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draft);

      const before = store.beforeYouStart();
      expect(before.dataScale.evidenceClassification).toBe('MEASURED');
      expect(before.dataScale.volumeEstimateLabel).toContain('8.4M');
    });

    it('provides duration range with medium confidence for bulk + cdc', () => {
      const draft = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draft);

      const before = store.beforeYouStart();
      expect(before.duration.isAvailable).toBe(true);
      expect(before.duration.rangeDisplay).toContain('1h 45m');
      expect(before.duration.confidenceLevel).toBe('MEDIUM');
    });

    it('provides fast DDL estimate with high confidence for schema only mode', () => {
      const draft = createMockDraft('M6_SCHEMA_ONLY');
      ms.updateDraft(draft);

      const before = store.beforeYouStart();
      expect(before.duration.rangeDisplay).toBe('1m – 3m');
      expect(before.duration.confidenceLevel).toBe('HIGH');
    });

    it('distinguishes downstream runtime barriers from pre-initialization blockers', () => {
      const draft = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draft);

      const before = store.beforeYouStart();
      expect(before.runtimeIntervention.hasDownstreamBarriers).toBe(true);
      expect(before.runtimeIntervention.downstreamBarrierCount).toBe(1);
      expect(before.runtimeIntervention.description).toContain('pause before cutover');
    });
  });

  // --------------------------------------------------------------------------
  // 4. EXECUTION TIMING & RECURRENCE
  // --------------------------------------------------------------------------
  describe('4. Execution Timing & Scheduling Controls', () => {
    it('defaults to Run Now with valid submit eligibility', () => {
      const timing = store.timingState();
      expect(timing.choice).toBe('RUN_NOW');
      expect(timing.isValid).toBe(true);
      expect(store.primaryCtaLabel()).toBe('Initialize & Launch');
    });

    it('updates timing choice to Schedule for Later with dynamic CTA', () => {
      store.setTimingChoice('SCHEDULE_LATER');

      const timing = store.timingState();
      expect(timing.choice).toBe('SCHEDULE_LATER');
      expect(store.primaryCtaLabel()).toBe('Schedule Migration');
    });

    it('formats resolved local and UTC timestamps for scheduled execution', () => {
      store.setTimingChoice('SCHEDULE_LATER');
      store.setScheduledDate('2026-10-15');
      store.setScheduledTime('23:30');
      store.setTimezone('Asia/Kolkata');

      const timing = store.timingState();
      expect(timing.resolvedLocalDisplay).toBeTruthy();
      expect(timing.resolvedUtcDisplay).toBeTruthy();
      expect(timing.isValid).toBe(true);
    });

    it('enforces recurrence mode restrictions (allowed for M1, forbidden for continuous M2)', () => {
      const draftM2 = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draftM2);
      expect(store.timingState().isRecurrencePermittedForMode).toBe(false);

      const draftM1 = createMockDraft('M1_BULK');
      ms.updateDraft(draftM1);
      expect(store.timingState().isRecurrencePermittedForMode).toBe(true);
    });
  });

  // --------------------------------------------------------------------------
  // 5. CONSEQUENCE EXPLAINER
  // --------------------------------------------------------------------------
  describe('5. What Happens Next Dynamic Consequence Explainer', () => {
    it('generates immediate execution consequences for Run Now', () => {
      store.setTimingChoice('RUN_NOW');
      const consequence = store.consequence();

      expect(consequence.title).toBe('Immediate Execution');
      expect(consequence.primaryActionDescription).toContain('begin execution immediately');
      expect(consequence.subsequentSteps.length).toBeGreaterThanOrEqual(3);
    });

    it('generates scheduled arming consequences for Schedule for Later', () => {
      store.setTimingChoice('SCHEDULE_LATER');
      store.setScheduledDate('2026-11-01');
      store.setScheduledTime('18:00');

      const consequence = store.consequence();
      expect(consequence.title).toBe('Scheduled Execution');
      expect(consequence.primaryActionDescription).toContain('initialize and arm');
    });

    it('includes restrained production notice when environment is Production', () => {
      const draft = createMockDraft('M2_BULK_CDC', 'Production');
      ms.updateDraft(draft);

      const consequence = store.consequence();
      expect(consequence.isProduction).toBe(true);
      expect(consequence.productionNotice).toContain('Production Migration');
    });
  });

  // --------------------------------------------------------------------------
  // 6. TECHNICAL DETAILS MODAL & OVERLAY
  // --------------------------------------------------------------------------
  describe('6. Technical Details Modal Management', () => {
    it('toggles technical modal open and closed', () => {
      expect(store.isTechnicalModalOpen()).toBe(false);

      store.openTechnicalModal();
      expect(store.isTechnicalModalOpen()).toBe(true);

      store.closeTechnicalModal();
      expect(store.isTechnicalModalOpen()).toBe(false);
    });

    it('provides complete technical metadata snapshot', () => {
      const draft = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draft);

      const tech = store.technicalDetails();
      expect(tech.migrationId).toBeTruthy();
      expect(tech.planId).toBeTruthy();
      expect(tech.planFingerprint).toBeTruthy();
      expect(tech.policyBinding).toContain('AKAAL-ENTERPRISE-GOVERNANCE');
      expect(tech.governanceSealStatus).toBe('SEALED & AUTHORIZED');
    });
  });

  // --------------------------------------------------------------------------
  // 7. FINAL ACTION ORCHESTRATION (RUN NOW & SCHEDULE)
  // --------------------------------------------------------------------------
  describe('7. Final Action Execution & Lifecycle Orchestration', () => {
    it('orchestrates Run Now initialization -> start -> navigation', async () => {
      const draft = createMockDraft('M2_BULK_CDC');
      ms.updateDraft(draft);

      store.setTimingChoice('RUN_NOW');

      const ipcInvokeSpy = vi.spyOn(ipc, 'invoke').mockResolvedValue({ status: 'SUCCESS' });

      await store.executeFinalAction();

      // Check IPC call sequence
      expect(ipcInvokeSpy).toHaveBeenCalledWith(
        'engine/migration',
        'initialize',
        expect.objectContaining({
          timingMode: 'RUN_NOW'
        })
      );
      expect(ipcInvokeSpy).toHaveBeenCalledWith(
        'engine/migration',
        'start',
        expect.objectContaining({
          migrationId: expect.any(String)
        })
      );

      // Check successful navigation to Mission Control
      expect(mockRouter.navigate).toHaveBeenCalledWith(
        expect.arrayContaining(['/migration', expect.any(String)])
      );
      expect(store.submitPhase()).toBe('SUCCESS');
    });

    it('orchestrates Schedule for Later initialization -> schedule -> navigation to portfolio', async () => {
      const draft = createMockDraft('M1_BULK');
      ms.updateDraft(draft);

      store.setTimingChoice('SCHEDULE_LATER');
      store.setScheduledDate('2026-12-01');
      store.setScheduledTime('02:00');

      const ipcInvokeSpy = vi.spyOn(ipc, 'invoke').mockResolvedValue({ status: 'SUCCESS' });

      await store.executeFinalAction();

      // Check IPC call sequence
      expect(ipcInvokeSpy).toHaveBeenCalledWith(
        'engine/migration',
        'initialize',
        expect.objectContaining({
          timingMode: 'SCHEDULE_LATER'
        })
      );
      expect(ipcInvokeSpy).toHaveBeenCalledWith(
        'engine/schedule',
        'create',
        expect.objectContaining({
          timezone: expect.any(String)
        })
      );

      // Check navigation to portfolio
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration/portfolio']);
      expect(store.submitPhase()).toBe('SUCCESS');
    });

    it('handles initialization failure gracefully without navigating', async () => {
      vi.spyOn(ipc, 'invoke').mockResolvedValue({
        status: 'ERROR',
        error: 'Database lock acquisition failed'
      });

      await store.executeFinalAction();

      expect(store.submitPhase()).toBe('ERROR');
      expect(store.operationError()?.phase).toBe('INITIALIZATION');
      expect(store.operationError()?.message).toContain('Database lock acquisition failed');
      expect(mockRouter.navigate).not.toHaveBeenCalled();
    });

    it('handles start dispatch failure after successful initialization', async () => {
      vi.spyOn(ipc, 'invoke')
        .mockResolvedValueOnce({ status: 'SUCCESS' }) // initialize succeeds
        .mockResolvedValueOnce({ status: 'ERROR', error: 'Worker partition pool timeout' }); // start fails

      await store.executeFinalAction();

      expect(store.submitPhase()).toBe('ERROR');
      expect(store.operationError()?.phase).toBe('START');
      expect(store.operationError()?.message).toContain('Worker partition pool timeout');
      expect(mockRouter.navigate).not.toHaveBeenCalled();
    });

    it('prevents double submission while submission is in flight', async () => {
      store.submitPhase.set('INITIALIZING');
      expect(store.isSubmitEligible()).toBe(false);

      const ipcInvokeSpy = vi.spyOn(ipc, 'invoke');
      await store.executeFinalAction();
      expect(ipcInvokeSpy).not.toHaveBeenCalled();
    });
  });

  // --------------------------------------------------------------------------
  // 8. UPSTREAM NAVIGATION
  // --------------------------------------------------------------------------
  describe('8. Upstream Review Step Navigation', () => {
    it('routes back to upstream steps on demand', () => {
      store.routeToUpstreamStep(4);
      expect(ms.wizardDraft().currentStep).toBe(4);

      store.routeToUpstreamStep(6);
      expect(ms.wizardDraft().currentStep).toBe(6);

      store.routeToUpstreamStep(8);
      expect(ms.wizardDraft().currentStep).toBe(8);
    });
  });
});
