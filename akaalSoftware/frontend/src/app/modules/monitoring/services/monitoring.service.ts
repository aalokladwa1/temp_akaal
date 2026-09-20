import { Injectable, signal, computed, inject } from '@angular/core';
import {
  OperationalSummaryDTO,
  NeedsAttentionCondition,
  ActiveMigrationOperationalItem,
  PlatformHealthArea,
  ResourcePressureMetric,
  MonitoringAlertItem,
  OperationalEventItem,
  FreshnessState,
  CanonicalMigrationMode
} from '../models/monitoring.models';
import {
  MonitoringIpcService,
  MigrationAggregateDTO,
  BackendMigrationMode,
  BackendMigrationLifecycleState,
  IncidentRecordDTO,
  IncidentSeverity as BackendIncidentSeverity,
  AlertRecordDTO,
  AlertLifecycleState as BackendAlertLifecycleState
} from '../../../core/services/ipc/monitoring.ipc';

// ---------------------------------------------------------------------------
// Real backend record -> Overview view-model projections. See
// migration-monitoring.service.ts / alerts-monitoring.service.ts for the
// same enum-mapping principle applied to their respective sub-modules; kept
// local here (not shared) since the target DTOs differ per sub-module.
// ---------------------------------------------------------------------------

const BACKEND_TO_CANONICAL_MODE: Record<Exclude<BackendMigrationMode, 'M8'>, CanonicalMigrationMode> = {
  M1: 'M1_BULK', M2: 'M2_BULK_CDC', M3: 'M3_CDC', M4: 'M4_INCREMENTAL',
  M5: 'M5_STATE_SYNC', M6: 'M6_SCHEMA_ONLY', M7: 'M7_DATA_ONLY'
};

function mapOperationalState(state: BackendMigrationLifecycleState): ActiveMigrationOperationalItem['operational_state'] {
  switch (state) {
    case 'ACTIVE': return 'ACTIVE';
    case 'PAUSING':
    case 'PAUSED': return 'PAUSED';
    case 'DRAFT': case 'CONFIGURING': case 'DISCOVERED': case 'PLANNED':
    case 'GOVERNANCE_PENDING': case 'AUTHORIZED': case 'INITIALIZED': return 'INITIALIZING';
    case 'COMPLETED': case 'ARCHIVED': return 'COMPLETED';
    case 'FAILED': case 'CANCELLED': return 'FAILED';
    default: return 'ATTENTION';
  }
}

function mapMigrationToOverviewItem(rec: MigrationAggregateDTO): ActiveMigrationOperationalItem | null {
  if (rec.mode === 'M8') return null;
  return {
    id: rec.migration_id,
    name: rec.name,
    source_provider: '',
    source_instance: '',
    target_provider: '',
    target_instance: '',
    mode: BACKEND_TO_CANONICAL_MODE[rec.mode as Exclude<BackendMigrationMode, 'M8'>],
    current_stage: '',
    operational_state: mapOperationalState(rec.state),
    health: 'UNKNOWN',
    progress_percent: null,
    observed_at: rec.updated_at,
    freshness_state: 'CURRENT',
    deep_link_route: `/monitoring/migration?id=${rec.migration_id}`
  };
}

function mapIncidentSeverityToUi(sev: BackendIncidentSeverity): 'CRITICAL' | 'WARNING' | 'INFO' | 'UNKNOWN' {
  if (sev === 'SEV1' || sev === 'SEV2') return 'CRITICAL';
  if (sev === 'SEV3') return 'WARNING';
  return 'INFO';
}

function mapIncidentToNeedsAttention(rec: IncidentRecordDTO): NeedsAttentionCondition {
  const ageMin = Math.max(0, Math.round((Date.now() - new Date(rec.created_at).getTime()) / 60000));
  return {
    id: rec.incident_id,
    entity_type: 'INCIDENT',
    entity_id: rec.incident_id,
    entity_name: rec.title,
    condition_title: rec.title,
    condition_detail: rec.summary,
    severity: mapIncidentSeverityToUi(rec.severity),
    duration_label: ageMin < 60 ? `${ageMin}m` : `${Math.round(ageMin / 60)}h`,
    direction: 'stable',
    deep_link_route: `/monitoring/alerts?incident=${rec.incident_id}`,
    deep_link_label: 'View Incident'
  };
}

function mapAlertLifecycleToUiStatus(state: BackendAlertLifecycleState): 'FIRING' | 'ACKNOWLEDGED' | 'RESOLVED' {
  if (state === 'OPEN' || state === 'REOPENED') return 'FIRING';
  if (state === 'ACKNOWLEDGED' || state === 'SUPPRESSED') return 'ACKNOWLEDGED';
  return 'RESOLVED';
}

function mapAlertToMonitoringAlertItem(rec: AlertRecordDTO): MonitoringAlertItem {
  return {
    id: rec.alert_id,
    alert_rule_name: rec.signal_name,
    severity: rec.severity === 'CRITICAL' ? 'CRITICAL' : rec.severity === 'HIGH' || rec.severity === 'MEDIUM' ? 'WARNING' : 'INFO',
    affected_entity: rec.signal_name,
    entity_type: 'SYSTEM',
    summary: rec.message,
    triggered_at: rec.first_observed_at,
    status: mapAlertLifecycleToUiStatus(rec.lifecycle_state),
    deep_link_route: '/monitoring/alerts'
  };
}

@Injectable({
  providedIn: 'root'
})
export class MonitoringService {
  private ipc: MonitoringIpcService;

  // Core State Signals
  public summary = signal<OperationalSummaryDTO | null>(null);
  public needsAttention = signal<NeedsAttentionCondition[]>([]);
  public activeMigrations = signal<ActiveMigrationOperationalItem[]>([]);
  // No canonical composite platform-health-by-area or resource-pressure-by-
  // dimension authority is wired to Monitoring today (LEGITIMATE_CAPABILITY_ABSENT) --
  // see Platform Monitoring, which has the same finding for its own richer surfaces.
  public platformHealth = signal<PlatformHealthArea[]>([]);
  public operationalPressure = signal<ResourcePressureMetric[]>([]);
  public activeAlerts = signal<MonitoringAlertItem[]>([]);
  // No canonical global operational-event-stream authority is wired to
  // Monitoring today (LEGITIMATE_CAPABILITY_ABSENT).
  public recentEvents = signal<OperationalEventItem[]>([]);

  // Status & Telemetry Signals
  public isLoading = signal<boolean>(true);
  public isRefreshing = signal<boolean>(false);
  public isUnavailable = signal<boolean>(false);
  public errorMessage = signal<string>('');
  public lastObservedAt = signal<string | null>(null);
  public telemetryConfidence = signal<FreshnessState>('NO_DATA' as FreshnessState);

  // Interactive Filter Signals
  public migrationSearchQuery = signal<string>('');
  public alertFilterSeverity = signal<string>('ALL'); // 'ALL' | 'CRITICAL' | 'WARNING'

  // Computed Derived Values
  public activeMigrationCount = computed(() => {
    return this.activeMigrations().filter(
      m => m.operational_state === 'ACTIVE' || m.operational_state === 'RUNNING'
    ).length;
  });

  public criticalAttentionCount = computed(() => {
    return this.needsAttention().filter(c => c.severity === 'CRITICAL').length;
  });

  public filteredActiveMigrations = computed(() => {
    const list = this.activeMigrations();
    const query = this.migrationSearchQuery().trim().toLowerCase();
    if (!query) return list;

    return list.filter(m =>
      m.name.toLowerCase().includes(query) ||
      m.source_provider.toLowerCase().includes(query) ||
      m.target_provider.toLowerCase().includes(query) ||
      m.current_stage.toLowerCase().includes(query)
    );
  });

  public filteredAlerts = computed(() => {
    const alerts = this.activeAlerts();
    const sev = this.alertFilterSeverity();
    if (sev === 'ALL') return alerts;
    return alerts.filter(a => a.severity === sev);
  });

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

  public async initializeState(): Promise<void> {
    this.isLoading.set(true);
    this.isUnavailable.set(false);
    this.errorMessage.set('');

    try {
      await this.fetchMonitoringData();
    } catch (err: any) {
      console.error('[MonitoringService] Failed to load initial monitoring state:', err);
      this.isUnavailable.set(true);
      this.errorMessage.set('Monitoring telemetry engine is currently unavailable.');
      this.telemetryConfidence.set('NO_DATA');
    } finally {
      this.isLoading.set(false);
    }
  }

  public async refresh(): Promise<void> {
    this.isRefreshing.set(true);
    try {
      await this.fetchMonitoringData();
    } catch (err: any) {
      console.error('[MonitoringService] Refresh error:', err);
      this.telemetryConfidence.set('STALE');
    } finally {
      this.isRefreshing.set(false);
    }
  }

  /**
   * Composes Overview state from real canonical read queries -- no single
   * "get_home_state" backend authority exists (the previous production code's
   * `akaal:monitoring`/`get_home_state` call had no matching handler anywhere
   * in the repository and always fell through to a hardcoded baseline).
   *
   *   summary.{active,total}_migrations_count, activeMigrations <- migration.list
   *   needsAttention          <- incident.list (unresolved incidents, projected
   *                              into the NeedsAttentionCondition INCIDENT entity_type)
   *   activeAlerts, summary.active_alerts_count <- alert.list
   *   summary.overall_platform_health/engine_connection_state <- fleet.status
   *     (deterministic mapping from real node liveness, same formula as
   *     PlatformMonitoringService.refresh())
   *
   * platform_health (per-area breakdown) and operational_pressure
   * (CPU/memory/storage/network/queues) and recentEvents (a global event
   * stream) have no canonical backend authority wired to Monitoring today and
   * are left truthfully empty rather than fabricated.
   */
  private async fetchMonitoringData(): Promise<void> {
    const [migrationsRes, incidentsRes, alertsRes, fleetRes] = await Promise.all([
      this.ipc.listMigrations({ limit: 200 }),
      this.ipc.listIncidents(),
      this.ipc.listAlerts(),
      this.ipc.getFleetStatus()
    ]);

    if (migrationsRes.status !== 'SUCCESS' || !migrationsRes.data) {
      this.isUnavailable.set(true);
      this.errorMessage.set(migrationsRes.error || 'Monitoring backend unavailable.');
      this.telemetryConfidence.set('NO_DATA');
      return;
    }

    const activeMigrations = migrationsRes.data.migrations
      .map(mapMigrationToOverviewItem)
      .filter((x): x is ActiveMigrationOperationalItem => x !== null);

    const needsAttention = incidentsRes.status === 'SUCCESS' && incidentsRes.data
      ? incidentsRes.data.incidents.filter(i => i.status !== 'RESOLVED' && i.status !== 'CLOSED').map(mapIncidentToNeedsAttention)
      : [];

    const activeAlerts = alertsRes.status === 'SUCCESS' && alertsRes.data
      ? alertsRes.data.alerts.map(mapAlertToMonitoringAlertItem)
      : [];

    const nodes = fleetRes.status === 'SUCCESS' && fleetRes.data ? fleetRes.data.nodes : [];
    const anyDead = nodes.some(n => n.liveness === 'DEAD');
    const anyDegraded = nodes.some(n => n.liveness === 'DEGRADED' || n.liveness === 'UNKNOWN');
    const overallHealth = anyDead ? 'UNHEALTHY' : anyDegraded ? 'DEGRADED' : nodes.length > 0 ? 'HEALTHY' : 'UNKNOWN';
    const engineConnectionState = fleetRes.status === 'SUCCESS' ? 'CONNECTED' : 'DISCONNECTED';

    const observedAt = new Date().toISOString();
    const summary: OperationalSummaryDTO = {
      overall_platform_health: overallHealth,
      telemetry_confidence: 'CURRENT',
      observed_at: observedAt,
      active_migrations_count: activeMigrations.filter(m => m.operational_state === 'ACTIVE' || m.operational_state === 'RUNNING').length,
      total_migrations_count: activeMigrations.length,
      attention_conditions_count: needsAttention.length,
      active_alerts_count: activeAlerts.filter(a => a.status === 'FIRING').length,
      engine_connection_state: engineConnectionState,
      headline_message: needsAttention.length > 0
        ? `${needsAttention.length} operational condition${needsAttention.length === 1 ? '' : 's'} require attention.`
        : 'No unresolved incidents reported by the canonical Alerts & Incidents authority.'
    };

    this.summary.set(summary);
    this.needsAttention.set(needsAttention);
    this.activeMigrations.set(activeMigrations);
    this.activeAlerts.set(activeAlerts);
    this.lastObservedAt.set(observedAt);
    this.telemetryConfidence.set('CURRENT');
    this.isUnavailable.set(false);
  }

  // Format label helper ensuring no snake_case leaks into UI
  public formatLabel(str: string | null | undefined): string {
    if (!str) return '';
    return str
      .replace(/_/g, ' ')
      .replace(/\b\w/g, char => char.toUpperCase())
      .replace(/\bCdc\b/gi, 'CDC')
      .replace(/\bDdl\b/gi, 'DDL')
      .replace(/\bWal\b/gi, 'WAL')
      .replace(/\bIpc\b/gi, 'IPC')
      .replace(/\bTls\b/gi, 'TLS')
      .replace(/\bSql\b/gi, 'SQL')
      .replace(/\bRds\b/gi, 'RDS')
      .replace(/\bDag\b/gi, 'DAG')
      .replace(/\bDb\b/gi, 'DB');
  }

  // Format sentence helper removing underscores while preserving sentence casing
  public formatSentence(str: string | null | undefined): string {
    if (!str) return '';
    return str
      .replace(/_/g, ' ')
      .replace(/\bcdc\b/gi, 'CDC')
      .replace(/\bddl\b/gi, 'DDL')
      .replace(/\bwal\b/gi, 'WAL')
      .replace(/\bipc\b/gi, 'IPC')
      .replace(/\btls\b/gi, 'TLS')
      .replace(/\bsql\b/gi, 'SQL');
  }

  // Format canonical timestamp helper
  public formatObservationTime(isoString: string | null): string {
    if (!isoString) return 'Unknown';
    try {
      const d = new Date(isoString);
      const diffMs = Date.now() - d.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      if (diffSec < 5) return 'Just now';
      if (diffSec < 60) return `${diffSec}s ago`;
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  }
}
