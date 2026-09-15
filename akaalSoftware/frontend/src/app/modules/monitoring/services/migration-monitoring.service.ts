import { Injectable, signal, computed } from '@angular/core';
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
  MOCK_MIGRATION_FLEET,
  MOCK_FLEET_SUMMARY,
  generateSelectedMigrationDetail
} from '../fixtures/migration-monitoring.fixtures';

@Injectable({
  providedIn: 'root'
})
export class MigrationMonitoringService {
  // Primary Store Signals
  public fleetList = signal<MigrationFleetItem[]>(MOCK_MIGRATION_FLEET);
  public summary = signal<FleetSummaryDTO | null>(MOCK_FLEET_SUMMARY);
  public selectedMigrationId = signal<string | null>(null);
  public selectedMigration = signal<SelectedMigrationFullDTO | null>(null);
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
  public lastObservedAt = signal<Date | null>(new Date());
  public telemetryConfidence = signal<FreshnessState>('CURRENT');

  // Computed Filtered Fleet
  public filteredFleet = computed(() => {
    const list = this.fleetList();
    const query = this.searchQuery().trim().toLowerCase();
    const mode = this.modeFilter();
    const health = this.healthFilter();
    const state = this.stateFilter();

    return list.filter(item => {
      // Search query matches name, project, source/target provider or instance
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

      // Mode filter (Canonical modes only: M1 to M7)
      if (mode !== 'ALL' && item.mode !== mode) {
        return false;
      }

      // Health filter
      if (health !== 'ALL' && item.health !== health) {
        return false;
      }

      // Operational state filter
      if (state !== 'ALL' && item.operational_state !== state) {
        return false;
      }

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

  constructor() {
    this.initializeState();
  }

  public initializeState(): void {
    try {
      this.isLoading.set(false);
      this.isUnavailable.set(false);
      this.errorMessage.set(null);
      this.fleetList.set(MOCK_MIGRATION_FLEET);
      this.summary.set(MOCK_FLEET_SUMMARY);
      this.lastObservedAt.set(new Date());
      this.telemetryConfidence.set('CURRENT');
    } catch (err: any) {
      this.isUnavailable.set(true);
      this.errorMessage.set(err?.message || 'Failed to connect to migration telemetry service.');
    }
  }

  public refresh(): void {
    this.isRefreshing.set(true);
    setTimeout(() => {
      this.isRefreshing.set(false);
      this.lastObservedAt.set(new Date());
      this.telemetryConfidence.set('CURRENT');

      // Refresh selected migration if one is active
      const activeId = this.selectedMigrationId();
      if (activeId) {
        this.loadSelectedMigrationDetail(activeId);
      }
    }, 300);
  }

  public selectMigration(id: string | null): void {
    this.selectedMigrationId.set(id);
    if (!id) {
      this.selectedMigration.set(null);
      return;
    }
    this.loadSelectedMigrationDetail(id);
  }

  public loadSelectedMigrationDetail(id: string): void {
    const found = this.fleetList().find(m => m.id === id);
    if (found) {
      const detail = generateSelectedMigrationDetail(found);
      this.selectedMigration.set(detail);
    } else {
      // Fallback: create mock detail with provided ID
      const fallbackItem: MigrationFleetItem = {
        id,
        name: `Migration ${id}`,
        project_id: 'proj-default',
        project_name: 'Default Project',
        source_provider: 'PostgreSQL',
        source_instance: 'pg-source-01.internal',
        target_provider: 'PostgreSQL',
        target_instance: 'pg-target-01.internal',
        mode: 'M2_BULK_CDC',
        current_stage: 'Continuous Change Stream',
        plan_version: 'v1.0.0',
        plan_fingerprint: 'sha256:00000000000000000000000000000000',
        operational_state: 'RUNNING',
        health: 'HEALTHY',
        progress_percent: 100,
        observed_at: new Date().toISOString(),
        freshness_state: 'CURRENT',
        attention_count: 0,
        alert_count: 0,
        deep_link_route: `/monitoring/migrations/${id}`
      };
      this.selectedMigration.set(generateSelectedMigrationDetail(fallbackItem));
    }
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
