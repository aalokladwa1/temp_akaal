/**
 * AKAAL Enterprise Migration Platform
 * Cockpit / Mission Control — Reactive Signal Store Service
 *
 * Governing Directives:
 * 1. Manages reactive state for live execution sessions.
 * 2. Unidirectional authority: Projects adapter models to presentation components.
 * 3. Handles canonical lifecycle actions, confirmation dialogs, and barrier resolution.
 */

import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { CockpitAdapterService } from './cockpit-adapter.service';
import { MigrationUiService } from './migration-ui.service';
import { IpcService } from './ipc.service';
import {
  CockpitIdentity,
  CockpitStatusPulse,
  WorkloadProgressState,
  RuntimeDagTopology,
  RuntimeDagNode,
  EngineHealthSummary,
  CurrentActivitySnapshot,
  DynamicWorkbenchData,
  ExecutionContextNarrative,
  OperatorIntervention,
  CanonicalPermittedAction,
  CockpitActivityEvent
} from '../../modules/migration/cockpit/cockpit.models';

@Injectable({
  providedIn: 'root'
})
export class CockpitStoreService {
  private adapter: CockpitAdapterService;
  private ms: MigrationUiService;
  private ipc: IpcService;
  private router: Router;

  constructor(
    adapter?: CockpitAdapterService,
    ms?: MigrationUiService,
    ipc?: IpcService,
    router?: Router
  ) {
    this.adapter = adapter || inject(CockpitAdapterService, { optional: true }) || new CockpitAdapterService();
    this.ms = ms || inject(MigrationUiService, { optional: true }) || new MigrationUiService();
    this.ipc = ipc || inject(IpcService, { optional: true }) || new IpcService();
    this.router = router || inject(Router, { optional: true }) as Router;

    if (typeof window !== 'undefined') {
      (window as any).__cockpitStore = this;
    }
  }

  // --------------------------------------------------------------------------
  // RAW REACTIVE STATE SIGNALS
  // --------------------------------------------------------------------------
  public session = signal<any>({
    id: 'MIG-2026-0906-A1',
    name: 'Core Banking Ledger Migration',
    environment: 'Production',
    mode: 'M2_BULK_CDC',
    sourceProvider: 'Oracle',
    sourceHost: 'orcl-prod.corp.internal',
    sourcePort: 1521,
    sourceDatabase: 'ORCLPDB',
    targetProvider: 'PostgreSQL',
    targetHost: 'pg-aurora.internal',
    targetPort: 5432,
    targetDatabase: 'finance',
    planRevision: 1,
    planFingerprint: '7f9a2b8e3c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f',
    activeAttempt: 1,
    lifecycleState: 'RUNNING',
    currentStage: 'Parallel Bulk Table Extraction & Load',
    activeTaskDescription: 'Copying CUSTOMER_LEDGER · Partition 18/32',
    activeEntityName: 'CUSTOMER_LEDGER',
    rowsProcessed: 418700000,
    rowsTotal: 600000000,
    progressPercent: 69.8,
    throughputRowsSec: 327000,
    throughputRowsSecFormatted: '327K',
    throughputBytesSecFormatted: '1.42 GB/s',
    etaString: '09:18',
    elapsedTimeString: '01:18:42',
    elapsedSec: 4722,
    activeWorkers: 16,
    cdcLagMs: 12,
    backlogMbFormatted: '14.2 MB',
    applyTxSecFormatted: '38.4K',
    convergenceState: 'CONVERGED',
    checkpointFreshness: '1.2s',
    isHealthDegraded: false
  });

  public selectedDagNodeId = signal<string | null>(null);
  public activeWorkbenchTab = signal<string>('data_movement');
  public isFullDagModalOpen = signal<boolean>(false);
  public pendingConfirmationAction = signal<CanonicalPermittedAction | null>(null);
  public actionInFlight = signal<boolean>(false);
  public eventFilterCategory = signal<string>('ALL');
  public copiedMigrationId = signal<boolean>(false);

  // --------------------------------------------------------------------------
  // COMPUTED PROJECTIONS (PURELY DERIVED VIA ADAPTER)
  // --------------------------------------------------------------------------
  public identity = computed<CockpitIdentity>(() => this.adapter.projectIdentity(this.session()));
  public statusPulse = computed<CockpitStatusPulse>(() => this.adapter.projectStatusPulse(this.session()));
  public workloadProgress = computed<WorkloadProgressState>(() => this.adapter.projectWorkloadProgress(this.session()));
  public runtimeDag = computed<RuntimeDagTopology>(() => this.adapter.projectRuntimeDag(this.session()));
  public activeNeighborhood = computed<RuntimeDagTopology>(() =>
    this.adapter.projectActiveNeighborhood(this.runtimeDag(), this.selectedDagNodeId() || undefined)
  );
  public selectedNode = computed<RuntimeDagNode | null>(() => {
    const id = this.selectedDagNodeId();
    if (!id) return null;
    return this.runtimeDag().nodes.find(n => n.id === id) || null;
  });

  public engineHealth = computed<EngineHealthSummary>(() => this.adapter.projectEngineHealth(this.session()));
  public currentActivity = computed<CurrentActivitySnapshot>(() => this.adapter.projectCurrentActivity(this.session()));
  public workbenchData = computed<DynamicWorkbenchData>(() =>
    this.adapter.projectWorkbenchDomains(this.session(), this.activeWorkbenchTab())
  );
  public executionContext = computed<ExecutionContextNarrative>(() => this.adapter.projectExecutionContext(this.session()));
  public intervention = computed<OperatorIntervention | null>(() => this.adapter.projectIntervention(this.session()));
  public permittedActions = computed<CanonicalPermittedAction[]>(() => this.adapter.projectPermittedActions(this.session()));
  public primaryAction = computed<CanonicalPermittedAction | null>(() =>
    this.permittedActions().find(a => a.isPrimary) || null
  );
  public secondaryActions = computed<CanonicalPermittedAction[]>(() =>
    this.permittedActions().filter(a => !a.isPrimary)
  );
  public activityEvents = computed<CockpitActivityEvent[]>(() => this.adapter.projectActivityEvents(this.session()));
  public filteredEvents = computed<CockpitActivityEvent[]>(() => {
    const cat = this.eventFilterCategory();
    const list = this.activityEvents();
    if (cat === 'ALL') return list;
    return list.filter(e => e.category === cat);
  });

  // --------------------------------------------------------------------------
  // STORE ACTIONS & LIFECYCLE MANAGEMENT
  // --------------------------------------------------------------------------
  public loadMigration(migrationId: string): void {
    // Check if matching migration exists in Portfolio
    const portfolio = this.ms.portfolioMigrations();
    const found = portfolio.find(m => m.id === migrationId);

    if (found) {
      this.session.update(s => ({
        ...s,
        id: found.id,
        name: found.name,
        mode: found.mode,
        environment: found.environment || 'Production',
        sourceProvider: found.sourceEngine || 'Oracle',
        targetProvider: found.targetEngine || 'PostgreSQL',
        lifecycleState: found.lifecycleState || 'RUNNING',
        currentStage: found.currentStage || 'Parallel Bulk Table Extraction & Load',
        progressPercent: found.progressPercent || 69.8,
        throughputRowsSecFormatted: `${Math.round((found.throughputRowsSec || 327000) / 1000)}K`,
        etaString: found.etaString || '09:18'
      }));
    }
  }

  public setSessionState(overrides: Partial<any>): void {
    this.session.update(s => ({ ...s, ...overrides }));
  }

  public selectDagNode(nodeId: string | null): void {
    this.selectedDagNodeId.set(nodeId);
  }

  public setActiveWorkbenchTab(tabId: string): void {
    this.activeWorkbenchTab.set(tabId);
  }

  public setEventFilter(category: string): void {
    this.eventFilterCategory.set(category);
  }

  public toggleFullDagModal(open?: boolean): void {
    this.isFullDagModalOpen.update(v => open !== undefined ? open : !v);
  }

  public copyMigrationId(): void {
    const id = this.identity().migrationId;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(id).then(() => {
        this.copiedMigrationId.set(true);
        setTimeout(() => this.copiedMigrationId.set(false), 2000);
      });
    }
  }

  // --------------------------------------------------------------------------
  // PERMITTED ACTION DISPATCH & CONFIRMATION
  // --------------------------------------------------------------------------
  public triggerAction(actionId: string): void {
    const action = this.permittedActions().find(a => a.id === actionId);
    if (!action || action.disabled) return;

    if (action.confirmationRequired) {
      this.pendingConfirmationAction.set(action);
    } else {
      this.executeActionDirectly(action);
    }
  }

  public confirmPendingAction(): void {
    const action = this.pendingConfirmationAction();
    if (!action) return;
    this.pendingConfirmationAction.set(null);
    this.executeActionDirectly(action);
  }

  public cancelPendingAction(): void {
    this.pendingConfirmationAction.set(null);
  }

  private async executeActionDirectly(action: CanonicalPermittedAction): Promise<void> {
    this.actionInFlight.set(true);

    try {
      if (action.id === 'PAUSE' || action.id === 'DRAIN_AND_PAUSE') {
        this.session.update(s => ({
          ...s,
          lifecycleState: 'PAUSED',
          throughputRowsSec: 0,
          throughputRowsSecFormatted: '0',
          activeWorkers: 0
        }));
      } else if (action.id === 'RESUME') {
        this.session.update(s => ({
          ...s,
          lifecycleState: 'RUNNING',
          throughputRowsSec: 327000,
          throughputRowsSecFormatted: '327K',
          activeWorkers: 16
        }));
      } else if (action.id === 'RECOVER_EXECUTION') {
        this.session.update(s => ({
          ...s,
          lifecycleState: 'RUNNING',
          isHealthDegraded: false,
          throughputRowsSec: 327000,
          throughputRowsSecFormatted: '327K',
          activeWorkers: 16
        }));
      } else if (action.id === 'TERMINATE') {
        this.session.update(s => ({
          ...s,
          lifecycleState: 'CANCELLED',
          throughputRowsSec: 0,
          activeWorkers: 0
        }));
      } else if (action.id === 'REVIEW_BARRIER') {
        this.session.update(s => ({ ...s, lifecycleState: 'WAITING_FOR_APPROVAL' }));
      } else if (action.id === 'REQUEST_CHECKPOINT') {
        this.session.update(s => ({
          ...s,
          checkpointFreshness: '0.1s fresh'
        }));
      } else if (action.id === 'RESCAN_HEALTH') {
        this.session.update(s => ({
          ...s,
          isHealthDegraded: false,
          lastHealthScan: new Date().toISOString()
        }));
      }
    } finally {
      this.actionInFlight.set(false);
    }
  }

  public resolveApprovalBarrier(barrierId: string, approved: boolean): void {
    this.actionInFlight.set(true);
    setTimeout(() => {
      if (approved) {
        this.session.update(s => ({
          ...s,
          lifecycleState: 'RUNNING',
          currentStage: 'Stage 6: Production Cutover & Source Quiesce'
        }));
      } else {
        this.session.update(s => ({
          ...s,
          lifecycleState: 'PAUSED',
          currentStage: 'Held at Approval Barrier'
        }));
      }
      this.actionInFlight.set(false);
    }, 400);
  }
}
