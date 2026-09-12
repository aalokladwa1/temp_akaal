/**
 * AKAAL Monitoring — Part 3 of 4: Platform Operations Models
 * Master semantic models for platform-wide observability, runtime services,
 * connectivity, infrastructure & fleet, capacity, performance, reliability, and diagnostics.
 */

import { FreshnessState, HealthState } from './monitoring.models';

export type PlatformTabKey = 
  | 'overview'
  | 'runtime'
  | 'connectivity'
  | 'infrastructure'
  | 'capacity'
  | 'performance'
  | 'reliability'
  | 'diagnostics';

export interface PlatformTabDefinition {
  key: PlatformTabKey;
  label: string;
}

export const PLATFORM_TABS: PlatformTabDefinition[] = [
  { key: 'overview', label: 'Platform Overview' },
  { key: 'runtime', label: 'Runtime & Services' },
  { key: 'connectivity', label: 'Connectivity & Endpoints' },
  { key: 'infrastructure', label: 'Infrastructure & Fleet' },
  { key: 'capacity', label: 'Capacity & Utilization' },
  { key: 'performance', label: 'Platform Performance' },
  { key: 'reliability', label: 'Platform Reliability' },
  { key: 'diagnostics', label: 'Diagnostics' }
];

// ============================================================================
// 1. PLATFORM OVERVIEW MODELS
// ============================================================================

export interface PlatformSummaryDTO {
  overall_health: HealthState;
  liveness_state: 'ALIVE' | 'DEGRADED' | 'DEAD';
  readiness_state: 'READY' | 'INITIALIZING' | 'NOT_READY';
  observed_at: string;
  freshness: FreshnessState;
  telemetry_confidence: string;
  active_alerts_count: number;
  unresolved_incidents_count: number;
  total_nodes: number;
  healthy_nodes: number;
  total_services: number;
  healthy_services: number;
  total_connectors: number;
  healthy_connectors: number;
  total_workers: number;
  active_workers: number;
  cpu_headroom_pct: number;
  memory_headroom_mb: number;
}

export interface PlatformConditionItem {
  id: string;
  title: string;
  subsystem: 'RUNTIME' | 'CONNECTIVITY' | 'INFRASTRUCTURE' | 'CAPACITY' | 'RELIABILITY';
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  summary: string;
  evidence: string;
  timestamp: string;
  target_tab: PlatformTabKey;
}

// ============================================================================
// 2. RUNTIME & SERVICES MODELS
// ============================================================================

export interface RuntimeServiceDTO {
  id: string;
  name: string;
  subsystem: string;
  role: string;
  status: 'ACTIVE' | 'STANDBY' | 'DEGRADED' | 'FAILED' | 'INITIALIZING';
  health: HealthState;
  availability_pct: number;
  p95_latency_ms: number;
  error_count_24h: number;
  version: string;
  liveness: 'PASS' | 'FAIL';
  readiness: 'PASS' | 'FAIL';
  dependencies_summary: string;
  last_heartbeat: string;
  description: string;
  memory_allocated_mb: number;
  goroutines_or_threads: number;
}

// ============================================================================
// 3. CONNECTIVITY & ENDPOINTS MODELS
// ============================================================================

export interface PlatformConnectorDTO {
  id: string;
  provider: string;
  family: 'RELATIONAL' | 'WAREHOUSE' | 'NOSQL' | 'STREAMING' | 'OBJECT_STORAGE';
  driver_status: 'AUTHENTICATED' | 'UNAUTHORIZED' | 'UNAVAILABLE' | 'NOT_CONFIGURED';
  reachability: 'REACHABLE' | 'DEGRADED' | 'UNREACHABLE';
  health: HealthState;
  active_connections: number;
  pool_max: number;
  rtt_latency_ms: number;
  endpoint_target: string;
  tls_enabled: boolean;
  notes: string;
}

export interface ExternalDependencyDTO {
  id: string;
  name: string;
  category: 'STATE_STORE' | 'RAFT_QUORUM' | 'SCHEMA_REGISTRY' | 'CACHE' | 'KMS_VAULT' | 'MESSAGE_BUS';
  health: HealthState;
  reachability: string;
  latency_ms: number;
  summary: string;
}

// ============================================================================
// 4. INFRASTRUCTURE & FLEET MODELS
// ============================================================================

export interface PlatformNodeDTO {
  node_id: string;
  host_name: string;
  role: 'PRIMARY_COMPUTE' | 'WORKER_NODE' | 'COORDINATOR' | 'EDGE_GATEWAY';
  region_locality: string;
  cluster_name: string;
  status: 'ACTIVE' | 'DRAINING' | 'STANDBY' | 'OFFLINE';
  health: HealthState;
  cpu_utilization_pct: number;
  memory_used_mb: number;
  memory_total_mb: number;
  allocated_slots: number;
  active_workers: number;
  uptime_hours: number;
  version: string;
  last_heartbeat: string;
}

export interface PlatformWorkerDTO {
  worker_id: string;
  node_id: string;
  host_name: string;
  status: 'BUSY' | 'IDLE' | 'ASSIGNED' | 'DRAINING';
  health: HealthState;
  assigned_migration_id?: string;
  assigned_migration_name?: string;
  assigned_partition?: string;
  rows_processed_count: number;
  work_rate_label: string;
  memory_mb: number;
  cpu_pct: number;
}

export interface DistributedLeaseDTO {
  lease_id: string;
  resource_name: string;
  owner_node_id: string;
  fencing_epoch: number;
  lease_duration_sec: number;
  expires_in_sec: number;
  is_valid: boolean;
  state: 'ACQUIRED' | 'RENEWING' | 'RELEASED' | 'EXPIRED';
}

// ============================================================================
// 5. CAPACITY & UTILIZATION MODELS
// ============================================================================

export interface PlatformCapacityDTO {
  cpu: {
    total_cores: number;
    used_pct: number;
    headroom_pct: number;
    status: 'NORMAL' | 'ELEVATED' | 'SATURATED';
  };
  memory: {
    total_mb: number;
    used_mb: number;
    used_pct: number;
    headroom_mb: number;
    status: 'NORMAL' | 'ELEVATED' | 'SATURATED';
  };
  storage_domains: {
    domain: string;
    used_mb: number;
    capacity_mb: number;
    used_pct: number;
    description: string;
  }[];
  network: {
    current_ingress_mbps: number;
    current_egress_mbps: number;
    bandwidth_capacity_mbps: number;
    status: 'NOMINAL' | 'ELEVATED';
  };
  queues: {
    ring_buffer_pct: number;
    spool_disk_pct: number;
    backpressure_level: 'NONE' | 'LOW' | 'HIGH';
  };
  forecasting: {
    sample_window: string;
    is_sufficient_samples: boolean;
    projected_exhaustion_days: number | null;
    advisory_notice: string;
  };
}

// ============================================================================
// 6. PLATFORM PERFORMANCE MODELS
// ============================================================================

export interface PlatformPerformanceDTO {
  work_rate: {
    total_rows_per_sec: number;
    total_bytes_per_sec_label: string;
    total_events_per_sec: number;
    trend: 'improving' | 'stable' | 'worsening';
  };
  latencies: {
    runtime_dispatch_ms: number;
    ipc_transit_ms: number;
    queue_buffer_ms: number;
    sink_apply_ms: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
  worker_skew: {
    total_workers: number;
    balanced_workers: number;
    elevated_workers: number;
    stragglers: number;
    skew_summary: string;
  };
  systemic_bottlenecks: {
    id: string;
    subsystem: string;
    severity: 'HIGH' | 'MEDIUM' | 'LOW';
    description: string;
    evidence: string;
  }[];
}

// ============================================================================
// 7. PLATFORM RELIABILITY MODELS
// ============================================================================

export interface PlatformReliabilityDTO {
  failure_events: {
    id: string;
    timestamp: string;
    component: string;
    error_code: string;
    message: string;
    is_recoverable: boolean;
  }[];
  recovery_progress: {
    active_recovery_count: number;
    successful_recoveries_24h: number;
    failed_recoveries_24h: number;
    current_strategy: string;
  };
  component_restarts: {
    component: string;
    restarts_24h: number;
    uptime_duration: string;
    churn_status: 'STABLE' | 'ELEVATED_CHURN';
  }[];
  durability: {
    checkpoint_store_integrity: 'VERIFIED_NOMINAL' | 'DEGRADED';
    raft_consensus_state: 'QUORUM_HEALTHY' | 'MINORITY';
    cas_lease_fencing_status: 'PROTECTED' | 'WARNING';
  };
  advisory_rca: {
    rank: number;
    candidate_cause: string;
    confidence_percent: number;
    epistemic_status: string;
    supporting_evidence: string;
  }[];
}

// ============================================================================
// 8. PLATFORM DIAGNOSTICS MODELS
// ============================================================================

export interface DiagnosticLogLine {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  logger: string;
  message: string;
}

export interface PlatformDiagnosticsDTO {
  correlation_context: {
    global_trace_id: string;
    run_id: string;
    session_id: string;
    engine_fingerprint: string;
  };
  bounded_logs: DiagnosticLogLine[];
  runtime_events: {
    id: string;
    timestamp: string;
    event_type: string;
    component: string;
    message: string;
    severity: 'INFO' | 'WARNING' | 'CRITICAL';
  }[];
  telemetry_exporters: {
    exporter_name: string;
    protocol: string;
    status: 'ACTIVE' | 'UNCONFIGURED' | 'DEGRADED';
    collector_endpoint: string;
    delivery_rate_pct: number;
  }[];
}

// Composite Master DTO for Platform Operations
export interface PlatformOperationsDTO {
  summary: PlatformSummaryDTO;
  conditions: PlatformConditionItem[];
  runtime_services: RuntimeServiceDTO[];
  connectors: PlatformConnectorDTO[];
  external_dependencies: ExternalDependencyDTO[];
  nodes: PlatformNodeDTO[];
  workers: PlatformWorkerDTO[];
  leases: DistributedLeaseDTO[];
  capacity: PlatformCapacityDTO;
  performance: PlatformPerformanceDTO;
  reliability: PlatformReliabilityDTO;
  diagnostics: PlatformDiagnosticsDTO;
}
