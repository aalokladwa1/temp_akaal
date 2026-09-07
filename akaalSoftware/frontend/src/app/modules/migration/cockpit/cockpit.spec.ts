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

    it('should open confirmation modal for destructive action and resolve upon confirm', () => {
      store.triggerAction('TERMINATE');
      expect(store.pendingConfirmationAction()).not.toBeNull();
      expect(store.pendingConfirmationAction()?.id).toBe('TERMINATE');

      store.confirmPendingAction();
      expect(store.pendingConfirmationAction()).toBeNull();
      expect(store.identity().lifecycleState).toBe('CANCELLED');
    });

    it('should resolve approval barrier and update stage when approved', async () => {
      store.resolveApprovalBarrier('barrier-cutover', true);
      expect(store.actionInFlight()).toBe(true);

      await new Promise(resolve => setTimeout(resolve, 450));
      expect(store.actionInFlight()).toBe(false);
      expect(store.identity().lifecycleState).toBe('RUNNING');
    });
  });
});
