/**
 * AKAAL Monitoring — Part 3 of 4: Platform Operations Service
 * Signal-driven reactive store managing platform overview, runtime services,
 * connectivity, infrastructure & fleet, capacity, performance, reliability, and diagnostics.
 *
 * Summary counts (nodes/alerts/incidents/health) are composed from real
 * canonical backend queries (fleet.status, alert.list, incident.list) via
 * monitoring.ipc.ts. The remaining detail surfaces -- runtime services,
 * connectors, per-node/per-worker rosters, capacity/performance/reliability
 * breakdowns, diagnostics -- have no canonical backend authority reachable
 * from Monitoring today; several of their required fields (node `role`,
 * connector `driver_status`, service `version`, etc.) have zero real source
 * and this service does not fabricate them. They are left at a truthful
 * empty/zero baseline (LEGITIMATE_CAPABILITY_ABSENT) rather than mock data.
 */

import { Injectable, signal, computed, inject } from '@angular/core';
import {
  PlatformOperationsDTO,
  PlatformTabKey,
  RuntimeServiceDTO,
  PlatformNodeDTO,
  PlatformConnectorDTO,
  PlatformWorkerDTO
} from '../models/platform-monitoring.models';
import { formatSnakeToTitle } from '../models/monitoring.models';
import { MonitoringIpcService } from '../../../core/services/ipc/monitoring.ipc';

const EMPTY_PLATFORM_OPERATIONS: PlatformOperationsDTO = {
  summary: {
    overall_health: 'UNKNOWN',
    liveness_state: 'DEGRADED',
    readiness_state: 'NOT_READY',
    observed_at: new Date(0).toISOString(),
    freshness: 'NO_DATA',
    telemetry_confidence: 'NO_DATA',
    active_alerts_count: 0,
    unresolved_incidents_count: 0,
    total_nodes: 0,
    healthy_nodes: 0,
    total_services: 0,
    healthy_services: 0,
    total_connectors: 0,
    healthy_connectors: 0,
    total_workers: 0,
    active_workers: 0,
    cpu_headroom_pct: 0,
    memory_headroom_mb: 0
  },
  conditions: [],
  runtime_services: [],
  connectors: [],
  external_dependencies: [],
  // Real fleet node identity/liveness IS available via fleet.status, but
  // PlatformNodeDTO.role ('PRIMARY_COMPUTE'|'WORKER_NODE'|'COORDINATOR'|
  // 'EDGE_GATEWAY') and several other required fields have no canonical
  // backend source -- left empty rather than assigning an invented role.
  nodes: [],
  workers: [],
  leases: [],
  capacity: {
    cpu: { total_cores: 0, used_pct: 0, headroom_pct: 0, status: 'NORMAL' },
    memory: { total_mb: 0, used_mb: 0, used_pct: 0, headroom_mb: 0, status: 'NORMAL' },
    storage_domains: [],
    network: { current_ingress_mbps: 0, current_egress_mbps: 0, bandwidth_capacity_mbps: 0, status: 'NOMINAL' },
    queues: { ring_buffer_pct: 0, spool_disk_pct: 0, backpressure_level: 'NONE' },
    forecasting: { sample_window: '', is_sufficient_samples: false, projected_exhaustion_days: null, advisory_notice: 'Capacity forecasting is not yet connected to Monitoring (LEGITIMATE_CAPABILITY_ABSENT).' }
  },
  performance: {
    work_rate: { total_rows_per_sec: 0, total_bytes_per_sec_label: '', total_events_per_sec: 0, trend: 'stable' },
    latencies: { runtime_dispatch_ms: 0, ipc_transit_ms: 0, queue_buffer_ms: 0, sink_apply_ms: 0, p50_ms: 0, p95_ms: 0, p99_ms: 0 },
    worker_skew: { total_workers: 0, balanced_workers: 0, elevated_workers: 0, stragglers: 0, skew_summary: '' },
    systemic_bottlenecks: []
  },
  reliability: {
    failure_events: [],
    recovery_progress: { active_recovery_count: 0, successful_recoveries_24h: 0, failed_recoveries_24h: 0, current_strategy: '' },
    component_restarts: [],
    // Unknown must never default to a positive/healthy claim with zero evidence
    // (fail-closed, matching this repo's own "missing authority != allow" pattern) --
    // these are the cautious/unverified-leaning members of each enum, not a claim
    // that anything is actually degraded.
    durability: { checkpoint_store_integrity: 'DEGRADED', raft_consensus_state: 'MINORITY', cas_lease_fencing_status: 'WARNING' },
    advisory_rca: []
  },
  diagnostics: {
    correlation_context: { global_trace_id: '', run_id: '', session_id: '', engine_fingerprint: '' },
    bounded_logs: [],
    runtime_events: [],
    telemetry_exporters: []
  }
};

@Injectable({
  providedIn: 'root'
})
export class PlatformMonitoringService {
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
    void this.refresh();
  }

  // Master Signal State
  private _data = signal<PlatformOperationsDTO>(EMPTY_PLATFORM_OPERATIONS);
  public data = computed(() => this._data());

  public isUnavailable = signal<boolean>(false);
  public errorMessage = signal<string | null>(null);

  // Active Tab & Selection Signals
  public selectedTab = signal<PlatformTabKey>('overview');
  public selectedNodeId = signal<string | null>(null);
  public selectedServiceId = signal<string | null>(null);

  // Search & Filter Signals
  public serviceSearchQuery = signal<string>('');
  public serviceStatusFilter = signal<string>('ALL');

  public nodeSearchQuery = signal<string>('');
  public nodeRoleFilter = signal<string>('ALL');

  public connectorSearchQuery = signal<string>('');
  public connectorFamilyFilter = signal<string>('ALL');

  // Refresh & Freshness State
  public isRefreshing = signal<boolean>(false);
  public lastObservedAt = signal<string>(EMPTY_PLATFORM_OPERATIONS.summary.observed_at);
  public telemetryConfidence = signal<string>(EMPTY_PLATFORM_OPERATIONS.summary.telemetry_confidence);

  // Formatter References
  public formatText = formatSnakeToTitle;

  // Computed Projections
  public summary = computed(() => this._data().summary);
  public conditions = computed(() => this._data().conditions);
  public capacity = computed(() => this._data().capacity);
  public performance = computed(() => this._data().performance);
  public reliability = computed(() => this._data().reliability);
  public diagnostics = computed(() => this._data().diagnostics);
  public leases = computed(() => this._data().leases);

  // Filtered Services
  public filteredServices = computed<RuntimeServiceDTO[]>(() => {
    const list = this._data().runtime_services;
    const q = this.serviceSearchQuery().trim().toLowerCase();
    const status = this.serviceStatusFilter();

    return list.filter(svc => {
      if (status !== 'ALL' && svc.status !== status) return false;
      if (q && !svc.name.toLowerCase().includes(q) && !svc.subsystem.toLowerCase().includes(q) && !svc.role.toLowerCase().includes(q)) return false;
      return true;
    });
  });

  // Selected Service Detail
  public selectedService = computed<RuntimeServiceDTO | null>(() => {
    const id = this.selectedServiceId();
    if (!id) return null;
    return this._data().runtime_services.find(s => s.id === id) || null;
  });

  // Filtered Nodes
  public filteredNodes = computed<PlatformNodeDTO[]>(() => {
    const list = this._data().nodes;
    const q = this.nodeSearchQuery().trim().toLowerCase();
    const role = this.nodeRoleFilter();

    return list.filter(node => {
      if (role !== 'ALL' && node.role !== role) return false;
      if (q && !node.host_name.toLowerCase().includes(q) && !node.node_id.toLowerCase().includes(q) && !node.region_locality.toLowerCase().includes(q)) return false;
      return true;
    });
  });

  // Selected Node Detail
  public selectedNode = computed<PlatformNodeDTO | null>(() => {
    const id = this.selectedNodeId();
    if (!id) return null;
    return this._data().nodes.find(n => n.node_id === id) || null;
  });

  // Workers allocated to selected node
  public selectedNodeWorkers = computed<PlatformWorkerDTO[]>(() => {
    const id = this.selectedNodeId();
    if (!id) return [];
    return this._data().workers.filter(w => w.node_id === id);
  });

  // Filtered Connectors
  public filteredConnectors = computed<PlatformConnectorDTO[]>(() => {
    const list = this._data().connectors;
    const q = this.connectorSearchQuery().trim().toLowerCase();
    const family = this.connectorFamilyFilter();

    return list.filter(conn => {
      if (family !== 'ALL' && conn.family !== family) return false;
      if (q && !conn.provider.toLowerCase().includes(q) && !conn.endpoint_target.toLowerCase().includes(q)) return false;
      return true;
    });
  });

  // State Mutators
  public selectTab(tabKey: PlatformTabKey): void {
    this.selectedTab.set(tabKey);
  }

  public selectNode(nodeId: string | null): void {
    this.selectedNodeId.set(nodeId);
  }

  public selectService(serviceId: string | null): void {
    this.selectedServiceId.set(serviceId);
  }

  public setServiceSearch(q: string): void {
    this.serviceSearchQuery.set(q);
  }

  public setServiceStatusFilter(s: string): void {
    this.serviceStatusFilter.set(s);
  }

  public setNodeSearch(q: string): void {
    this.nodeSearchQuery.set(q);
  }

  public setNodeRoleFilter(r: string): void {
    this.nodeRoleFilter.set(r);
  }

  public setConnectorSearch(q: string): void {
    this.connectorSearchQuery.set(q);
  }

  public setConnectorFamilyFilter(f: string): void {
    this.connectorFamilyFilter.set(f);
  }

  /**
   * Composes real summary counts from three canonical read queries:
   *   total_nodes / healthy_nodes / overall_health / liveness_state / readiness_state
   *     <- fleet.status (akaalPipeline FleetOperationalService.list_fleet_nodes)
   *   active_alerts_count      <- alert.list (AlertService.list_alerts, OPEN+ACKNOWLEDGED)
   *   unresolved_incidents_count <- incident.list (IncidentService.list_incidents, status != RESOLVED/CLOSED)
   * overall_health/liveness_state/readiness_state are a deterministic
   * presentation mapping from real node liveness: DEAD present -> DEAD/UNHEALTHY;
   * else DEGRADED present -> DEGRADED; else ALIVE -> ALIVE/HEALTHY.
   * readiness_state mirrors liveness_state (READY iff liveness_state === 'ALIVE').
   * All other summary counts (services/connectors/workers/headroom) have no
   * canonical source composed in this pass and remain 0 (LEGITIMATE_CAPABILITY_ABSENT).
   */
  public async refresh(): Promise<void> {
    this.isRefreshing.set(true);
    this.errorMessage.set(null);
    try {
      const [fleetRes, alertsRes, incidentsRes] = await Promise.all([
        this.ipc.getFleetStatus(),
        this.ipc.listAlerts(),
        this.ipc.listIncidents()
      ]);

      if (fleetRes.status !== 'SUCCESS' || !fleetRes.data) {
        this.isUnavailable.set(true);
        this.errorMessage.set(fleetRes.error || 'Fleet backend unavailable.');
        return;
      }

      const nodes = fleetRes.data.nodes;
      const totalNodes = nodes.length;
      const healthyNodes = nodes.filter(n => n.liveness === 'ALIVE').length;
      const anyDead = nodes.some(n => n.liveness === 'DEAD');
      const anyDegraded = nodes.some(n => n.liveness === 'DEGRADED' || n.liveness === 'UNKNOWN');
      const overallHealth = anyDead ? 'UNHEALTHY' : anyDegraded ? 'DEGRADED' : totalNodes > 0 ? 'HEALTHY' : 'UNKNOWN';
      const livenessState = anyDead ? 'DEAD' : anyDegraded ? 'DEGRADED' : totalNodes > 0 ? 'ALIVE' : 'DEGRADED';

      const activeAlertsCount = alertsRes.status === 'SUCCESS' && alertsRes.data
        ? alertsRes.data.alerts.filter(a => a.lifecycle_state === 'OPEN' || a.lifecycle_state === 'ACKNOWLEDGED').length
        : 0;
      const unresolvedIncidentsCount = incidentsRes.status === 'SUCCESS' && incidentsRes.data
        ? incidentsRes.data.incidents.filter(i => i.status !== 'RESOLVED' && i.status !== 'CLOSED').length
        : 0;

      const observedAt = new Date().toISOString();
      this._data.set({
        ...EMPTY_PLATFORM_OPERATIONS,
        summary: {
          ...EMPTY_PLATFORM_OPERATIONS.summary,
          overall_health: overallHealth as any,
          liveness_state: livenessState as any,
          readiness_state: livenessState === 'ALIVE' ? 'READY' : 'NOT_READY',
          observed_at: observedAt,
          freshness: 'CURRENT',
          telemetry_confidence: 'CURRENT',
          active_alerts_count: activeAlertsCount,
          unresolved_incidents_count: unresolvedIncidentsCount,
          total_nodes: totalNodes,
          healthy_nodes: healthyNodes
        }
      });
      this.lastObservedAt.set(observedAt);
      this.telemetryConfidence.set('CURRENT');
      this.isUnavailable.set(false);
    } catch (err: any) {
      this.isUnavailable.set(true);
      this.errorMessage.set(err?.message || 'Platform telemetry refresh failed.');
    } finally {
      this.isRefreshing.set(false);
    }
  }
}
