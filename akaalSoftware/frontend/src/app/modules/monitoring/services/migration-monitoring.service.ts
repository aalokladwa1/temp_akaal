import { Injectable, signal, computed, inject } from '@angular/core';
import {
  MigrationFleetItem,
  FleetSummaryDTO,
  SelectedMigrationFullDTO,
  MigrationTabKey,
  HealthState,
  FreshnessState,
  CanonicalMigrationMode
} from '../models/migration-monitoring.models';
import {
  MonitoringIpcService,
  MigrationAggregateDTO,
  BackendMigrationMode,
  BackendMigrationLifecycleState
} from '../../../core/services/ipc/monitoring.ipc';

// ---------------------------------------------------------------------------
// Backend MigrationAggregate -> frozen-UI MigrationFleetItem projection.
// Field-verified: akaalPipeline/state/aggregates.py MigrationAggregate.to_dict()
// via migration.list (akaalPipeline/application/unified_caller.py).
//
// mode: backend MigrationMode enum VALUES are literally "M1".."M8"
// (akaalPipeline/contracts/enums.py) -- a direct lookup to the frontend's
// CanonicalMigrationMode codes. M8 (validation-only) is excluded from
// Migration Monitoring per this module's own documented product principle.
//
// operational_state: backend MigrationLifecycleState has 15 real values
// (akaalPipeline/contracts/enums.py) that don't 1:1 match the frontend's
// 7-value operational_state union. This is a deterministic, documented,
// lossy presentation mapping -- never an invented value.
// ---------------------------------------------------------------------------

const BACKEND_TO_CANONICAL_MODE: Record<Exclude<BackendMigrationMode, 'M8'>, CanonicalMigrationMode> = {
  M1: 'M1_BULK',
  M2: 'M2_BULK_CDC',
  M3: 'M3_CDC',
  M4: 'M4_INCREMENTAL',
  M5: 'M5_STATE_SYNC',
  M6: 'M6_SCHEMA_ONLY',
  M7: 'M7_DATA_ONLY'
};

function mapOperationalState(state: BackendMigrationLifecycleState): MigrationFleetItem['operational_state'] {
  switch (state) {
    case 'ACTIVE': return 'ACTIVE';
    case 'PAUSING':
    case 'PAUSED': return 'PAUSED';
    case 'DRAFT':
    case 'CONFIGURING':
    case 'DISCOVERED':
    case 'PLANNED':
    case 'GOVERNANCE_PENDING':
    case 'AUTHORIZED':
    case 'INITIALIZED': return 'INITIALIZING';
    case 'COMPLETED':
    case 'ARCHIVED': return 'COMPLETED';
    case 'FAILED':
    case 'CANCELLED': return 'FAILED';
    case 'CANCELLATION_PENDING': return 'ATTENTION';
    default: return 'ATTENTION';
  }
}

function mapMigrationAggregateToFleetItem(rec: MigrationAggregateDTO): MigrationFleetItem | null {
  if (rec.mode === 'M8') {
    // M8 (validation-only) is explicitly excluded from Migration Monitoring
    // per this module's own product principle (see migration-monitoring.models.ts header).
    return null;
  }
  return {
    id: rec.migration_id,
    name: rec.name,
    // No canonical backend field currently exposes a human project name distinct
    // from project_id, or resolved source/target provider/instance labels --
    // those live inside `configuration`/`lineage` opaque dicts with no confirmed
    // key schema. Left truthfully empty rather than guessed (LEGITIMATE_CAPABILITY_ABSENT).
    project_id: rec.project_id ?? '',
    project_name: '',
    source_provider: '',
    source_instance: '',
    target_provider: '',
    target_instance: '',
    mode: BACKEND_TO_CANONICAL_MODE[rec.mode as Exclude<BackendMigrationMode, 'M8'>],
    current_stage: '',
    plan_version: rec.plan_id ?? '',
    plan_fingerprint: '',
    operational_state: mapOperationalState(rec.state),
    // Per-migration health requires a health.get_explainable() call per row;
    // not composed into the roster list in this pass (N+1 cost) -- UNKNOWN is
    // a real HealthState value, not fabricated.
    health: 'UNKNOWN',
    progress_percent: null,
    work_unit_label: undefined,
    throughput_label: undefined,
    lag_label: undefined,
    observed_at: rec.updated_at,
    freshness_state: 'CURRENT',
    attention_count: 0,
    alert_count: 0,
    deep_link_route: `/monitoring/migration?id=${rec.migration_id}`
  };
}

@Injectable({
  providedIn: 'root'
})
export class MigrationMonitoringService {
  private ipc: MonitoringIpcService;

  constructor(monitoringIpc?: MonitoringIpcService) {
    if (monitoringIpc) {
      this.ipc = monitoringIpc;
    } else {
      try {
        this.ipc = inject(MonitoringIpcService, { optional: true }) || new MonitoringIpcService();
      } catch {
        this.ipc = new MonitoringIpcService();
      }
    }
    void this.initializeState();
  }

  // Primary Store Signals
  public fleetList = signal<MigrationFleetItem[]>([]);
  public summary = signal<FleetSummaryDTO | null>(null);
  public selectedMigrationId = signal<string | null>(null);
  public selectedMigration = signal<SelectedMigrationFullDTO | null>(null);
  // True when a migration is selected and real, but its deep 8-tab telemetry
  // composite (per-endpoint driver status, per-worker skew, RCA hypotheses,
  // DAG stage state, etc.) has no canonical backend source today
  // (LEGITIMATE_CAPABILITY_ABSENT / OWNER_DECISION_REQUIRED -- see DevKros
  // CHECK2 + P7.D Monitoring integration walkthrough). The frozen UI's own
  // `@if (mms.selectedMigrationId() && mms.selectedMigration())` guard
  // (migration-monitoring-home.component.ts:97) already renders nothing in
  // this state, so no UI change was needed to represent it truthfully.
  public selectedMigrationDetailUnavailable = signal<boolean>(false);
  public selectedTab = signal<MigrationTabKey>('overview');

  // Filter Signals
  public searchQuery = signal<string>('');
  public modeFilter = signal<string>('ALL');
  public healthFilter = signal<string>('ALL');
  public stateFilter = signal<string>('ALL');

  // Engine Lifecycle Signals
  public isLoading = signal<boolean>(false);
  public isRefreshing = signal<boolean>(false);
  public isUnavailable = signal<boolean>(false);
  public errorMessage = signal<string | null>(null);
  public lastObservedAt = signal<Date | null>(null);
  public telemetryConfidence = signal<FreshnessState>('NO_DATA' as FreshnessState);

  // Computed Filtered Fleet
  public filteredFleet = computed(() => {
    const list = this.fleetList();
    const query = this.searchQuery().trim().toLowerCase();
    const mode = this.modeFilter();
    const health = this.healthFilter();
    const state = this.stateFilter();

    return list.filter(item => {
      if (query) {
        const matchesName = item.name.toLowerCase().includes(query);
        const matchesProject = item.project_name.toLowerCase().includes(query);
        const matchesSource = `${item.source_provider} ${item.source_instance}`.toLowerCase().includes(query);
        const matchesTarget = `${item.target_provider} ${item.target_instance}`.toLowerCase().includes(query);
        const matchesStage = item.current_stage.toLowerCase().includes(query);
        if (!matchesName && !matchesProject && !matchesSource && !matchesTarget && !matchesStage) {
          return false;
        }
      }
      if (mode !== 'ALL' && item.mode !== mode) return false;
      if (health !== 'ALL' && item.health !== health) return false;
      if (state !== 'ALL' && item.operational_state !== state) return false;
      return true;
    });
  });

  // Computed Fleet Metrics
  public fleetCountSummary = computed(() => {
    const list = this.fleetList();
    const total = list.length;
    const running = list.filter(m => m.operational_state === 'RUNNING' || m.operational_state === 'ACTIVE').length;
    const attention = list.filter(m => m.operational_state === 'ATTENTION' || m.health === 'DEGRADED' || m.health === 'UNHEALTHY').length;
    const healthy = list.filter(m => m.health === 'HEALTHY').length;
    return { total, running, attention, healthy };
  });

  public async initializeState(): Promise<void> {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    try {
      const res = await this.ipc.listMigrations({ limit: 200 });
      if (res.status !== 'SUCCESS' || !res.data || !Array.isArray(res.data.migrations)) {
        this.isUnavailable.set(true);
        this.errorMessage.set(res.error || 'Migration fleet backend unavailable.');
        this.telemetryConfidence.set('NO_DATA');
        return;
      }

      const items = res.data.migrations
        .map(mapMigrationAggregateToFleetItem)
        .filter((x): x is MigrationFleetItem => x !== null);

      const observedAt = new Date().toISOString();
      const summary: FleetSummaryDTO = {
        total_fleet_count: items.length,
        active_fleet_count: items.filter(m => m.operational_state === 'ACTIVE' || m.operational_state === 'RUNNING').length,
        attention_fleet_count: items.filter(m => m.operational_state === 'ATTENTION').length,
        degraded_fleet_count: items.filter(m => m.health === 'DEGRADED').length,
        healthy_fleet_count: items.filter(m => m.health === 'HEALTHY').length,
        // No canonical real-time aggregated-throughput authority is wired to
        // Monitoring today (LEGITIMATE_CAPABILITY_ABSENT).
        aggregated_throughput_label: '',
        observed_at: observedAt,
        telemetry_confidence: 'CURRENT'
      };

      this.fleetList.set(items);
      this.summary.set(summary);
      this.lastObservedAt.set(new Date());
      this.telemetryConfidence.set('CURRENT');
      this.isUnavailable.set(false);
    } catch (err: any) {
      this.isUnavailable.set(true);
      this.errorMessage.set(err?.message || 'Failed to connect to migration telemetry service.');
      this.telemetryConfidence.set('NO_DATA');
    } finally {
      this.isLoading.set(false);
    }
  }

  public async refresh(): Promise<void> {
    this.isRefreshing.set(true);
    try {
      await this.initializeState();
      const activeId = this.selectedMigrationId();
      if (activeId) {
        await this.loadSelectedMigrationDetail(activeId);
      }
    } finally {
      this.isRefreshing.set(false);
    }
  }

  public selectMigration(id: string | null): void {
    this.selectedMigrationId.set(id);
    if (!id) {
      this.selectedMigration.set(null);
      this.selectedMigrationDetailUnavailable.set(false);
      return;
    }
    void this.loadSelectedMigrationDetail(id);
  }

  /**
   * The 8-tab per-migration detail composite (SelectedMigrationFullDTO) requires
   * per-endpoint driver status, per-worker skew classification, RCA hypotheses,
   * DAG stage state, and checkpoint/lease detail that has no canonical backend
   * authority today -- akaalPipeline's real per-migration queries
   * (observability.get / health.get_explainable / diagnostics.capture) return
   * opaque engine-defined telemetry dicts and a health causal chain, neither of
   * which maps onto this composite's ~15 forced-choice enum fields without
   * inventing values. Rather than fabricate operational truth, this method sets
   * selectedMigration to null (the frozen UI's own @if guard already renders
   * nothing in that state -- no UI change required) and flags
   * selectedMigrationDetailUnavailable so a future owner-approved backend
   * extension can replace this. See DevKros CHECK2 + P7.D Monitoring
   * integration walkthrough, Migration Monitoring section, for the full trace.
   */
  public async loadSelectedMigrationDetail(id: string): Promise<void> {
    const found = this.fleetList().find(m => m.id === id);
    if (!found) {
      this.selectedMigration.set(null);
      this.selectedMigrationDetailUnavailable.set(false);
      return;
    }
    this.selectedMigration.set(null);
    this.selectedMigrationDetailUnavailable.set(true);
  }

  public selectTab(tabKey: MigrationTabKey): void {
    this.selectedTab.set(tabKey);
  }

  public setSearchQuery(query: string): void {
    this.searchQuery.set(query);
  }

  public setModeFilter(mode: string): void {
    this.modeFilter.set(mode);
  }

  public setHealthFilter(health: string): void {
    this.healthFilter.set(health);
  }

  public setStateFilter(state: string): void {
    this.stateFilter.set(state);
  }

  public resetFilters(): void {
    this.searchQuery.set('');
    this.modeFilter.set('ALL');
    this.healthFilter.set('ALL');
    this.stateFilter.set('ALL');
  }

  // Formatting & Display Helpers
  public formatModeLabel(mode: CanonicalMigrationMode | string): string {
    switch (mode) {
      case 'M1_BULK': return 'Bulk Snapshot';
      case 'M2_BULK_CDC': return 'Bulk + CDC';
      case 'M3_CDC': return 'Continuous CDC';
      case 'M4_INCREMENTAL': return 'Incremental Polling';
      case 'M5_STATE_SYNC': return 'State-Based Sync';
      case 'M6_SCHEMA_ONLY': return 'Schema Only';
      case 'M7_DATA_ONLY': return 'Data Only';
      default: return mode.replace(/_/g, ' ');
    }
  }

  public formatHealthLabel(health: HealthState): string {
    switch (health) {
      case 'HEALTHY': return 'Healthy';
      case 'DEGRADED': return 'Degraded';
      case 'UNHEALTHY': return 'Unhealthy';
      case 'UNKNOWN': return 'Unknown';
      default: return health;
    }
  }

  public formatOperationalState(state: string): string {
    switch (state) {
      case 'ACTIVE': return 'Active';
      case 'RUNNING': return 'Running';
      case 'PAUSED': return 'Paused';
      case 'ATTENTION': return 'Needs Attention';
      case 'INITIALIZING': return 'Initializing';
      case 'COMPLETED': return 'Completed';
      case 'FAILED': return 'Failed';
      default: return state.replace(/_/g, ' ');
    }
  }
}
