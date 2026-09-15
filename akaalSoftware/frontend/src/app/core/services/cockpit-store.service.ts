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
  public loadMigration(migrationId: string): void {
    // Check if matching migration exists in Portfolio
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

    try {
      const actionMap: Record<string, string> = {
        PAUSE: 'pause',
        DRAIN_AND_PAUSE: 'pause',
        RESUME: 'resume',
        RECOVER_EXECUTION: 'resume',
        TERMINATE: 'terminate',
        REQUEST_CHECKPOINT: 'checkpoint',
        RESCAN_HEALTH: 'health_check'
      };

      const backendAction = actionMap[action.id];
      if (backendAction) {
        const res = await this.ipc.invoke('engine/migration', backendAction, {
          migrationId: this.identity().migrationId
        });

        if (!res || res.status !== 'SUCCESS') {
          console.error(`[CockpitStoreService] Action ${action.id} failed or unconfirmed`);
          this.actionInFlight.set(false);
          return;
        }
      }

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
          lifecycleState: 'RUNNING'
        }));
      } else if (action.id === 'RECOVER_EXECUTION') {
        this.session.update(s => ({
          ...s,
          lifecycleState: 'RUNNING',
          isHealthDegraded: false
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
