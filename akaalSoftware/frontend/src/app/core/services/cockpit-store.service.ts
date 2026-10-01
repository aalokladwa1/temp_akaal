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
import { MigrationIpc } from './ipc/migration.ipc';
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
  private migrationIpc: MigrationIpc;
  private router: Router;

  constructor(
    adapter?: CockpitAdapterService,
    ms?: MigrationUiService,
    ipc?: IpcService,
    router?: Router,
    migrationIpc?: MigrationIpc
  ) {
    try { this.adapter = adapter || inject(CockpitAdapterService); } catch { this.adapter = adapter || new CockpitAdapterService(); }
    try { this.ms = ms || inject(MigrationUiService); } catch { this.ms = ms || new MigrationUiService(); }
    try { this.ipc = ipc || inject(IpcService); } catch { this.ipc = ipc || new IpcService(); }
    try { this.router = router || inject(Router); } catch { this.router = router as any; }
    try { this.migrationIpc = migrationIpc || inject(MigrationIpc); } catch { this.migrationIpc = migrationIpc || new MigrationIpc(this.ipc); }

    if (typeof window !== 'undefined') {
      (window as any).__cockpitStore = this;
    }
    this.setupTelemetrySubscription();
  }

  // --------------------------------------------------------------------------
  // RAW REACTIVE STATE SIGNALS
  // --------------------------------------------------------------------------
  public session = signal<any>(null);

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
  public async loadMigration(migrationId: string): Promise<void> {
    try {
      const res = await this.migrationIpc.getMigration(migrationId);
      if (res && res.status === 'SUCCESS' && res.data) {
        const m = res.data;
        this.session.set({
          id: m.migration_id || m.id,
          name: m.name,
          mode: m.mode,
          environment: m.tenant_id || 'Production',
          sourceProvider: m.configuration?.source_provider || 'Oracle',
          targetProvider: m.configuration?.target_provider || 'PostgreSQL',
          lifecycleState: m.state || m.lifecycle_state,
          currentStage: m.current_stage || 'Configured',
          progressPercent: m.progress_percent ?? 0,
          throughputRowsSecFormatted: m.throughput_rows_per_sec ? `${Math.round(m.throughput_rows_per_sec / 1000)}K` : '0',
          etaString: m.etaString || 'Indeterminate'
        });
        return;
      }
    } catch (err) {
      console.warn('[CockpitStoreService] Failed to load migration from MigrationIpc:', err);
    }

    const portfolio = this.ms.portfolioMigrations();
    const found = portfolio.find(m => m.id === migrationId);

    if (found) {
      this.session.set({
        id: found.id,
        name: found.name,
        mode: found.mode,
        environment: found.environment || 'Production',
        sourceProvider: found.sourceEngine || 'Oracle',
        targetProvider: found.targetEngine || 'PostgreSQL',
        lifecycleState: found.lifecycleState || 'RUNNING',
        currentStage: found.currentStage || 'Parallel Bulk Table Extraction & Load',
        progressPercent: found.progressPercent ?? 0,
        throughputRowsSecFormatted: found.throughputRowsSec ? `${Math.round(found.throughputRowsSec / 1000)}K` : '0',
        etaString: found.etaString || 'Indeterminate'
      });
    } else {
      this.session.set(null);
    }
  }

  public setSessionState(overrides: Partial<any>): void {
    this.session.update(s => s ? ({ ...s, ...overrides }) : null);
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
    if (id && navigator.clipboard) {
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

  public async confirmPendingAction(): Promise<void> {
    const action = this.pendingConfirmationAction();
    if (!action) return;
    this.pendingConfirmationAction.set(null);
    await this.executeActionDirectly(action);
  }

  public cancelPendingAction(): void {
    this.pendingConfirmationAction.set(null);
  }

  private async executeActionDirectly(action: CanonicalPermittedAction): Promise<void> {
    this.actionInFlight.set(true);
    const migId = this.identity().migrationId;

    try {
      if (action.id === 'PAUSE' || action.id === 'DRAIN_AND_PAUSE') {
        if (this.migrationIpc && typeof this.migrationIpc.pauseMigration === 'function') {
          await this.migrationIpc.pauseMigration({ migration_id: migId }).catch(() => null);
        }
        this.session.update(s => ({
          ...s,
          lifecycleState: 'PAUSED',
          throughputRowsSec: 0,
          throughputRowsSecFormatted: '0',
          activeWorkers: 0
        }));
      } else if (action.id === 'RESUME') {
        if (this.migrationIpc && typeof this.migrationIpc.resumeMigration === 'function') {
          await this.migrationIpc.resumeMigration({ migration_id: migId }).catch(() => null);
        }
        this.session.update(s => ({
          ...s,
          lifecycleState: 'RUNNING'
        }));
      } else if (action.id === 'RECOVER_EXECUTION') {
        if (this.migrationIpc && typeof this.migrationIpc.recoverMigration === 'function') {
          await this.migrationIpc.recoverMigration({ migration_id: migId }).catch(() => null);
        }
        this.session.update(s => ({
          ...s,
          lifecycleState: 'RUNNING',
          isHealthDegraded: false
        }));
      } else if (action.id === 'TERMINATE') {
        if (this.migrationIpc && typeof this.migrationIpc.cancelMigration === 'function') {
          await this.migrationIpc.cancelMigration({ migration_id: migId }).catch(() => null);
        }
        this.session.update(s => ({
          ...s,
          lifecycleState: 'CANCELLED',
          throughputRowsSec: 0,
          activeWorkers: 0
        }));
      } else if (action.id === 'REVIEW_BARRIER') {
        this.session.update(s => ({ ...s, lifecycleState: 'WAITING_FOR_APPROVAL' }));
      } else if (action.id === 'CUTOVER' || action.id === 'APPROVE_BARRIER') {
        if (this.migrationIpc && typeof (this.migrationIpc as any).cutoverMigration === 'function') {
          await (this.migrationIpc as any).cutoverMigration({ migration_id: migId }).catch(() => null);
        }
        this.session.update(s => ({
          ...s,
          lifecycleState: 'COMPLETED',
          currentStage: 'Production Cutover & Source Quiesce',
          throughputRowsSec: 0,
          throughputRowsSecFormatted: '0',
          activeWorkers: 0
        }));
      } else if (action.id === 'LAUNCH_VALIDATION') {
        if (migId && this.router) {
          this.router.navigate(['/validation/new'], { queryParams: { migrationId: migId } });
        }
      } else if (action.id === 'REQUEST_CHECKPOINT') {
        if (this.migrationIpc && typeof this.migrationIpc.triggerCheckpoint === 'function') {
          await this.migrationIpc.triggerCheckpoint({ migration_id: migId }).catch(() => null);
        }
        this.session.update(s => ({
          ...s,
          checkpointFreshness: '0.1s fresh'
        }));
      } else if (action.id === 'RESCAN_HEALTH' || action.id === 'REFRESH_HEALTH') {
        let isDegraded = this.session()?.isHealthDegraded ?? false;
        if (migId && this.migrationIpc && typeof this.migrationIpc.getReadiness === 'function') {
          try {
            const res = await this.migrationIpc.getReadiness({ migration_id: migId });
            if (res && res.data) {
              isDegraded = res.data.overall_status === 'DEGRADED' || res.data.overall_status === 'NOT_READY' || res.data.overall_status === 'BLOCKED' || res.data.is_ready === false;
            }
          } catch {
            isDegraded = true;
          }
        }
        this.session.update(s => s ? ({
          ...s,
          isHealthDegraded: isDegraded,
          lastHealthScan: new Date().toISOString()
        }) : null);
      }
    } catch (err) {
      console.error(`[CockpitStoreService] Action ${action.id} failed:`, err);
    } finally {
      this.actionInFlight.set(false);
    }
  }

  public async resolveApprovalBarrier(barrierId: string, approved: boolean): Promise<void> {
    const cur = this.session();
    const migId = cur?.id;
    this.actionInFlight.set(true);
    try {
      const decision = approved ? 'APPROVED' : 'REJECTED';
      if (migId && this.migrationIpc && typeof this.migrationIpc.approveMigration === 'function') {
        const res = await this.migrationIpc.approveMigration({
          migration_id: migId,
          barrier_id: barrierId,
          decision: decision,
          reason: approved ? 'Approved by operator in Cockpit' : `Barrier ${barrierId} rejected by operator in Cockpit`
        });
        if (res && res.status === 'ERROR') {
          console.error(`[CockpitStoreService] Approval barrier decision ${decision} rejected by backend:`, res.error);
          return;
        }
      }
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
          currentStage: 'Held at Approval Barrier (Decision: REJECTED)'
        }));
      }
    } catch (err) {
      console.error(`[CockpitStoreService] resolveApprovalBarrier failed:`, err);
    } finally {
      this.actionInFlight.set(false);
    }
  }

  private setupTelemetrySubscription(): void {
    if (!this.ipc || typeof this.ipc.subscribe !== 'function') return;
    this.ipc.subscribe('akaal:telemetry', (payload: any) => {
      const current = this.session();
      if (!current || !payload) return;
      if (payload.migration_id && payload.migration_id !== current.id) return;

      this.session.update(s => {
        if (!s) return null;
        const progress = payload.progress_percent !== undefined ? payload.progress_percent : s.progressPercent;
        const throughput = payload.throughput_rows_per_sec !== undefined ? payload.throughput_rows_per_sec : s.throughputRowsSec;
        const throughputFormatted = throughput !== undefined ? `${Math.round(throughput / 1000)}K` : s.throughputRowsSecFormatted;
        return {
          ...s,
          progressPercent: progress,
          throughputRowsSec: throughput,
          throughputRowsSecFormatted: throughputFormatted,
          activeWorkers: payload.active_workers !== undefined ? payload.active_workers : s.activeWorkers,
          totalWorkers: payload.total_workers !== undefined ? payload.total_workers : s.totalWorkers,
          cdcLagMs: payload.cdc_lag_ms !== undefined ? payload.cdc_lag_ms : s.cdcLagMs,
          currentStage: payload.current_stage || s.currentStage,
          elapsedTimeString: payload.elapsed_time_string || s.elapsedTimeString,
          etaString: payload.eta_string || s.etaString,
          tableProgressList: payload.table_progress_list || s.tableProgressList,
          lastTelemetryTimestamp: new Date().toISOString()
        };
      });
    });
  }
}
