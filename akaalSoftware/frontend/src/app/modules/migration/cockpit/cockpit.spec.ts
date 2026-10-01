// ============================================================================
// AKAAL COCKPIT / MISSION CONTROL — MASTER UNIT TEST SUITE (VITEST)
// ============================================================================

import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { CockpitAdapterService } from '../../../core/services/cockpit-adapter.service';
import { CockpitStoreService } from '../../../core/services/cockpit-store.service';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { IpcService } from '../../../core/services/ipc.service';

describe('AKAAL Cockpit / Mission Control Unit Tests', () => {
  let adapter: CockpitAdapterService;
  let ms: MigrationUiService;
  let ipc: IpcService;
  let mockRouter: any;
  let store: CockpitStoreService;

  beforeEach(() => {
    adapter = new CockpitAdapterService();
    ms = new MigrationUiService();
    ipc = new IpcService();
    mockRouter = {
      navigate: vi.fn()
    };
    store = new CockpitStoreService(adapter, ms, ipc, mockRouter);
  });

  describe('1. Adapter Canonical Projections & Truth Preservation', () => {
    it('should project CockpitIdentity with exact endpoints, fingerprint and elapsed time', () => {
      const rawSession = {
        id: 'MIG-001',
        name: 'Enterprise DB Migration',
        mode: 'M2_BULK_CDC',
        environment: 'Staging',
        sourceProvider: 'Oracle',
        sourceHost: 'oracle.db.internal',
        sourcePort: 1521,
        sourceDatabase: 'PRODDB',
        targetProvider: 'PostgreSQL',
        targetHost: 'pg.db.internal',
        targetPort: 5432,
        targetDatabase: 'appdb',
        planRevision: 2,
        planFingerprint: 'abcdef0123456789abcdef0123456789',
        activeAttempt: 1,
        lifecycleState: 'RUNNING',
        elapsedTimeString: '02:15:30'
      };

      const identity = adapter.projectIdentity(rawSession);
      expect(identity.migrationId).toBe('MIG-001');
      expect(identity.modeTitle).toBe('Bulk Migration + Continuous CDC');
      expect(identity.source.provider).toBe('Oracle');
      expect(identity.target.provider).toBe('PostgreSQL');
      expect(identity.planRevision).toBe(2);
      expect(identity.lifecycleState).toBe('RUNNING');
      expect(identity.elapsedTimeString).toBe('02:15:30');
    });

    it('should project mode-specific metrics for M1 Bulk mode', () => {
      const session = {
        mode: 'M1_BULK',
        lifecycleState: 'RUNNING',
        currentStage: 'Table Extraction',
        throughputRowsSecFormatted: '250K',
        throughputBytesSecFormatted: '850 MB/s',
        etaString: '12:00',
        activeWorkers: 12
      };

      const pulse = adapter.projectStatusPulse(session);
      expect(pulse.metrics.length).toBeGreaterThanOrEqual(4);
      expect(pulse.metrics.some(m => m.id === 'throughput')).toBe(true);
      expect(pulse.metrics.some(m => m.id === 'workers')).toBe(true);
    });

    it('should project mode-specific metrics for M3 CDC Continuous mode', () => {
      const session = {
        mode: 'M3_CDC',
        lifecycleState: 'RUNNING',
        currentStage: 'Continuous Change Streaming',
        cdcLagMs: 8,
        backlogMbFormatted: '4.5 MB',
        applyTxSecFormatted: '15.2K'
      };

      const pulse = adapter.projectStatusPulse(session);
      expect(pulse.metrics.some(m => m.id === 'cdc_lag')).toBe(true);
      expect(pulse.metrics.find(m => m.id === 'cdc_lag')?.value).toBe('8');
      expect(pulse.metrics.find(m => m.id === 'cdc_lag')?.unit).toBe('ms');
    });

    it('should project collection-oriented EngineHealthSummary with causal degraded detection', () => {
      const session = {
        isHealthDegraded: true
      };

      const health = adapter.projectEngineHealth(session);
      expect(health.overallStatus).toBe('DEGRADED');
      expect(health.subsystems.length).toBeGreaterThan(0);
      expect(health.primaryDegradedReason).toBeDefined();
      expect(health.subsystems.some(s => s.isCausal)).toBe(true);
    });

    it('should project operator intervention when in WAITING_FOR_APPROVAL state', () => {
      const session = {
        lifecycleState: 'WAITING_FOR_APPROVAL',
        currentStage: 'Cutover Approval Barrier'
      };

      const intervention = adapter.projectIntervention(session);
      expect(intervention).not.toBeNull();
      expect(intervention?.type).toBe('APPROVAL_BARRIER');
      expect(intervention?.validActions.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('2. Store Signal State & Permitted Actions', () => {
    it('should update active workbench tab reactively', () => {
      expect(store.activeWorkbenchTab()).toBe('data_movement');
      store.setActiveWorkbenchTab('cdc_convergence');
      expect(store.activeWorkbenchTab()).toBe('cdc_convergence');
    });

    it('should select DAG node and derive selectedNode computed signal', () => {
      expect(store.selectedDagNodeId()).toBeNull();
      expect(store.selectedNode()).toBeNull();

      const topology = store.runtimeDag();
      if (topology.nodes.length > 0) {
        const firstNodeId = topology.nodes[0].id;
        store.selectDagNode(firstNodeId);
        expect(store.selectedDagNodeId()).toBe(firstNodeId);
        expect(store.selectedNode()?.id).toBe(firstNodeId);
      }
    });

    it('should open confirmation modal for destructive action and resolve upon confirm', async () => {
      store.triggerAction('TERMINATE');
      expect(store.pendingConfirmationAction()).not.toBeNull();
      expect(store.pendingConfirmationAction()?.id).toBe('TERMINATE');

      await store.confirmPendingAction();
      expect(store.pendingConfirmationAction()).toBeNull();
      expect(store.identity().lifecycleState).toBe('CANCELLED');
    });

    it('should resolve approval barrier and update stage when approved', async () => {
      await store.resolveApprovalBarrier('barrier-cutover', true);
      expect(store.actionInFlight()).toBe(false);
      expect(store.identity().lifecycleState).toBe('RUNNING');
    });
  });

  describe('3. Permitted Actions State Classification & Cutover Projection', () => {
    it('should expose Perform Cutover as primary action when state is CDC_STREAMING for M2_BULK_CDC mode', () => {
      const session = {
        mode: 'M2_BULK_CDC',
        lifecycleState: 'CDC_STREAMING'
      };

      const actions = adapter.projectPermittedActions(session);
      const cutoverAction = actions.find(a => a.id === 'CUTOVER');
      expect(cutoverAction).toBeDefined();
      expect(cutoverAction?.label).toBe('Perform Cutover');
      expect(cutoverAction?.isPrimary).toBe(true);

      const pauseAction = actions.find(a => a.id === 'PAUSE');
      expect(pauseAction).toBeDefined();
      expect(pauseAction?.isPrimary).toBe(false);
    });

    it('should NOT expose Perform Cutover during BULK_COMPLETED, IN_PROGRESS, or DISPATCHED phases', () => {
      for (const bulkState of ['BULK_COMPLETED', 'IN_PROGRESS', 'DISPATCHED']) {
        const session = {
          mode: 'M2_BULK_CDC',
          lifecycleState: bulkState
        };

        const actions = adapter.projectPermittedActions(session);
        const cutoverAction = actions.find(a => a.id === 'CUTOVER');
        expect(cutoverAction).toBeUndefined();

        const pauseAction = actions.find(a => a.id === 'PAUSE');
        expect(pauseAction).toBeDefined();
        expect(pauseAction?.isPrimary).toBe(true);
      }
    });

    it('should preserve Perform Cutover for RUNNING and ACTIVE states in M2_BULK_CDC mode', () => {
      for (const activeState of ['RUNNING', 'ACTIVE']) {
        const session = {
          mode: 'M2_BULK_CDC',
          lifecycleState: activeState
        };

        const actions = adapter.projectPermittedActions(session);
        const cutoverAction = actions.find(a => a.id === 'CUTOVER');
        expect(cutoverAction).toBeDefined();
        expect(cutoverAction?.isPrimary).toBe(true);
      }
    });

    it('should NOT manufacture Cutover for terminal states or non-streaming modes', () => {
      const terminalSession = {
        mode: 'M2_BULK_CDC',
        lifecycleState: 'COMPLETED'
      };
      const terminalActions = adapter.projectPermittedActions(terminalSession);
      expect(terminalActions.find(a => a.id === 'CUTOVER')).toBeUndefined();

      const bulkModeSession = {
        mode: 'M1_BULK',
        lifecycleState: 'CDC_STREAMING'
      };
      const bulkModeActions = adapter.projectPermittedActions(bulkModeSession);
      expect(bulkModeActions.find(a => a.id === 'CUTOVER')).toBeUndefined();
    });

    it('should expose Launch Validation Mission as primary action when state is COMPLETED or CUTOVER', () => {
      for (const st of ['COMPLETED', 'CUTOVER']) {
        const session = {
          mode: 'M2_BULK_CDC',
          lifecycleState: st
        };
        const actions = adapter.projectPermittedActions(session);
        const valAction = actions.find(a => a.id === 'LAUNCH_VALIDATION');
        expect(valAction).toBeDefined();
        expect(valAction?.isPrimary).toBe(true);
        expect(valAction?.label).toBe('Launch Validation Mission');
      }
    });

    it('should NOT expose Launch Validation Mission during active or failed execution states', () => {
      for (const st of ['RUNNING', 'ACTIVE', 'CDC_STREAMING', 'PAUSED', 'FAILED', 'CANCELLED', 'INITIALIZING']) {
        const session = {
          mode: 'M2_BULK_CDC',
          lifecycleState: st
        };
        const actions = adapter.projectPermittedActions(session);
        const valAction = actions.find(a => a.id === 'LAUNCH_VALIDATION');
        expect(valAction).toBeUndefined();
      }
    });

    it('should navigate to /validation/new with queryParams on LAUNCH_VALIDATION action trigger', () => {
      store.session.set({
        ...store.session(),
        id: 'MIG-999',
        lifecycleState: 'COMPLETED'
      });
      store.triggerAction('LAUNCH_VALIDATION');
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/validation/new'], {
        queryParams: { migrationId: 'MIG-999' }
      });
    });
  });
});

