/**
 * AKAAL MONITORING — PART 2 OF 4: MIGRATION OPERATIONS
 * Master Data Contracts & Semantic State Models
 * 
 * Strict Product Principles:
 * - Subject-First Navigation: Migration Fleet -> Selected Migration (8 Investigation Areas)
 * - Composed State Matrix: Applicability, Configuration, Authorization, Availability, Health, Freshness, Completeness
 * - Truthful Progress: Unknown totals remain null, continuous CDC remains continuous (no fake 0% or ETAs)
 * - Mode-Aware: M1 through M7 fully typed; M8 strictly excluded from Migration Monitoring
 * - Advisory Intelligence: RCA and Anomalies are advisory hypotheses with confidence and evidence
 */

import {
  HealthState,
  FreshnessState,
  SeverityLevel,
  TrendDirection,
  ApplicabilityState,
  ConfigurationState,
  AuthorizationState,
  AvailabilityState,
  CompletenessState,
  CanonicalMigrationMode,
  CANONICAL_MODES
} from './monitoring.models';

export type {
  HealthState,
  FreshnessState,
  SeverityLevel,
  TrendDirection,
  ApplicabilityState,
  ConfigurationState,
  AuthorizationState,
  AvailabilityState,
  CompletenessState,
  CanonicalMigrationMode
};
export { CANONICAL_MODES };

export type MigrationTabKey = 
  | 'overview'
  | 'execution'
  | 'performance'
  | 'resources'
  | 'health'
  | 'reliability'
  | 'alerts'
  | 'diagnostics';

export interface TabDefinition {
  key: MigrationTabKey;
  label: string;
  shortDescription: string;
  icon?: string;
  badgeCount?: number;
}

export const MIGRATION_TABS: TabDefinition[] = [
  { key: 'overview', label: 'Overview', shortDescription: 'Orientation, sync state, and active conditions' },
  { key: 'execution', label: 'Execution', shortDescription: 'ExecutionPlan, dynamic DAG, and mode telemetry' },
  { key: 'performance', label: 'Performance & Flow', shortDescription: 'Throughput rates, latencies, worker skew, and flow' },
  { key: 'resources', label: 'Resources & Placement', shortDescription: 'Attributed compute, memory, storage, and worker placement' },
  { key: 'health', label: 'Health & Dependencies', shortDescription: '7-dimensional composed health across all endpoints' },
  { key: 'reliability', label: 'Reliability & Recovery', shortDescription: 'Failures, checkpoints, resilience, and advisory RCA' },
  { key: 'alerts', label: 'Alerts & Incidents', shortDescription: 'Contextual firing alerts and linked incident telemetry' },
  { key: 'diagnostics', label: 'Diagnostics', shortDescription: 'Scoped correlation context, runtime logs, and traces' }
];

/** ========================================================================= */
/** 1. MIGRATION FLEET DATA MODELS                                            */
/** ========================================================================= */

export interface MigrationFleetItem {
  id: string;
  name: string;
  project_id: string;
  project_name: string;
  source_provider: string;
  source_instance: string;
  target_provider: string;
  target_instance: string;
  mode: CanonicalMigrationMode;
  current_stage: string;
  plan_version: string;
  plan_fingerprint: string;
  operational_state: 'ACTIVE' | 'RUNNING' | 'PAUSED' | 'ATTENTION' | 'INITIALIZING' | 'COMPLETED' | 'FAILED';
  health: HealthState;
  progress_percent?: number | null; // null if unknown total or continuous stream
  work_unit_label?: string; // e.g. "14.2M / 16.1M rows"
  throughput_label?: string; // e.g. "18,400 rows/s"
  lag_label?: string; // e.g. "380ms CDC lag"
  observed_at: string; // ISO 8601
  freshness_state: FreshnessState;
  attention_count: number;
  alert_count: number;
  deep_link_route: string;
}

export interface FleetSummaryDTO {
  total_fleet_count: number;
  active_fleet_count: number;
  attention_fleet_count: number;
  degraded_fleet_count: number;
  healthy_fleet_count: number;
  aggregated_throughput_label: string;
  observed_at: string;
  telemetry_confidence: FreshnessState;
}

/** ========================================================================= */
/** 2. SELECTED MIGRATION CONTEXT                                             */
/** ========================================================================= */

export interface SelectedMigrationHeaderDTO {
  id: string;
  name: string;
  project_id: string;
  project_name: string;
  source_provider: string;
  source_instance: string;
  target_provider: string;
  target_instance: string;
  mode: CanonicalMigrationMode;
  current_phase?: string;
  current_stage: string;
  plan_version: string;
  plan_fingerprint: string;
  operational_state: 'ACTIVE' | 'RUNNING' | 'PAUSED' | 'ATTENTION' | 'INITIALIZING' | 'COMPLETED' | 'FAILED';
  health: HealthState;
  observed_at: string;
  freshness_state: FreshnessState;
}

/** ========================================================================= */
/** 3. AREA 1: OVERVIEW                                                       */
/** ========================================================================= */

export interface MigrationOverviewDTO {
  sync_state_summary: string;
  semantic_work_headline: string;
  active_conditions: Array<{
    id: string;
    title: string;
    detail: string;
    severity: SeverityLevel;
    duration_label: string;
    direction: TrendDirection;
    action_label?: string;
  }>;
  recent_events: Array<{
    id: string;
    timestamp: string;
    category: string;
    summary: string;
    severity: SeverityLevel;
  }>;
}

/** ========================================================================= */
/** 4. AREA 2: EXECUTION & MODE-AWARE TELEMETRY                              */
/** ========================================================================= */

export interface DagStageNode {
  id: string;
  label: string;
  stage_type: 'SCHEMA' | 'SNAPSHOT' | 'BULK_DATA' | 'CDC_CATCHUP' | 'STREAM' | 'VALIDATION' | 'DRAIN';
  state: 'COMPLETED' | 'RUNNING' | 'WAITING' | 'BLOCKED' | 'SKIPPED';
  progress_percent?: number | null;
  rows_transferred?: number;
  duration_label: string;
  blocking_reason?: string;
}

export interface ExecutionPlanInfo {
  version: string;
  fingerprint: string;
  compiled_at: string;
  total_nodes: number;
  completed_nodes: number;
  active_node_label: string;
}

// Mode Specific Execution Telemetry
export interface M1BulkExecutionTelemetry {
  rows_transferred: number;
  bytes_transferred: number;
  total_rows?: number | null;
  total_bytes?: number | null;
  active_partitions: number;
  total_partitions: number;
  workers_active: number;
  target_write_latency_ms: number;
  checkpoint_freshness_seconds: number;
}

export interface M2BulkCdcExecutionTelemetry {
  current_phase: 'BULK_LOAD' | 'CDC_CATCHUP' | 'CONTINUOUS_SYNC' | 'CUTOVER_READINESS';
  bulk_rows_completed: number;
  bulk_total_rows?: number | null;
  bulk_progress_pct?: number | null;
  cdc_replication_lag_ms: number;
  cdc_backlog_rows: number;
  cdc_capture_rate_per_sec: number;
  cdc_apply_rate_per_sec: number;
  cutover_readiness_signals: {
    remaining_backlog_rows: number;
    current_lag_ms: number;
    schema_barriers_count: number;
    quarantined_events_count: number;
    source_health: HealthState;
    target_health: HealthState;
  };
}

export interface M3CdcExecutionTelemetry {
  capture_rate_per_sec: number;
  apply_rate_per_sec: number;
  replication_lag_ms: number;
  backlog_events: number;
  backlog_bytes: number;
  commit_position_label: string;
  ring_buffer_fill_pct: number;
  conflicts_detected: number;
  quarantined_events: number;
  checkpoint_freshness_sec: number;
  ack_freshness_sec: number;
}

export interface M4IncrementalExecutionTelemetry {
  watermark_field: string;
  watermark_current_value: string;
  polling_cadence_seconds: number;
  last_poll_timestamp: string;
  last_poll_latency_ms: number;
  delta_rows_discovered: number;
  delta_rows_applied: number;
  batch_size: number;
  is_stale: boolean;
}

export interface M5StateSyncExecutionTelemetry {
  scan_cycle_number: number;
  scan_duration_ms: number;
  entities_scanned: number;
  differences_discovered: number;
  drift_detected_count: number;
  reconciliation_backlog: number;
  reconciliation_apply_rate_per_sec: number;
  unresolved_differences: number;
}

export interface M6SchemaExecutionTelemetry {
  objects_discovered: number;
  objects_converted: number;
  objects_applied: number;
  ddl_work_rate_per_sec: number;
  current_object_name: string;
  blocked_dependencies_count: number;
  unsupported_objects_count: number;
  manual_review_required_count: number;
  average_ddl_latency_ms: number;
}

export interface M7DataOnlyExecutionTelemetry {
  rows_transferred: number;
  bytes_transferred: number;
  transfer_rate_rows_per_sec: number;
  active_table: string;
  active_partition: string;
  coercion_errors_count: number;
  target_commit_latency_ms: number;
  spool_buffer_active: boolean;
  checkpoint_freshness_sec: number;
}

export interface MigrationExecutionDTO {
  plan_info: ExecutionPlanInfo;
  dag_nodes: DagStageNode[];
  m1_bulk?: M1BulkExecutionTelemetry;
  m2_bulk_cdc?: M2BulkCdcExecutionTelemetry;
  m3_cdc?: M3CdcExecutionTelemetry;
  m4_incremental?: M4IncrementalExecutionTelemetry;
  m5_state_sync?: M5StateSyncExecutionTelemetry;
  m6_schema?: M6SchemaExecutionTelemetry;
  m7_data_only?: M7DataOnlyExecutionTelemetry;
}

/** ========================================================================= */
/** 5. AREA 3: PERFORMANCE & FLOW                                             */
/** ========================================================================= */

export interface WorkerPerformanceItem {
  id: string;
  name: string;
  role: string;
  assigned_partition: string;
  rows_processed: number;
  rate_label: string;
  cpu_percent: number;
  memory_mb: number;
  skew_state: 'BALANCED' | 'ELEVATED' | 'STRAGGLER';
}

export interface BottleneckObservation {
  id: string;
  subsystem: string;
  severity: SeverityLevel;
  description: string;
  trend: TrendDirection;
  evidence: string;
}

export interface MigrationPerformanceDTO {
  work_rate_label: string;
  work_rate_unit: string;
  work_rate_trend: TrendDirection;
  latencies: {
    source_read_ms: number;
    queue_buffer_ms: number;
    sink_apply_ms: number;
    cdc_replication_lag_ms: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
  flow: {
    ring_buffer_pct: number;
    spool_disk_pct: number;
    backpressure_level: 'NONE' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
    queue_saturation_pct: number;
  };
  workers: WorkerPerformanceItem[];
  bottlenecks: BottleneckObservation[];
}

/** ========================================================================= */
/** 6. AREA 4: RESOURCES & PLACEMENT                                          */
/** ========================================================================= */

export interface AssignedNodeItem {
  node_id: string;
  host_name: string;
  region_locality: string;
  slots_allocated: number;
  active_workers: number;
  migration_cpu_pct: number;
  migration_memory_mb: number;
  health: HealthState;
  platform_route: string;
}

export interface AssignedPartitionItem {
  partition_id: string;
  partition_name: string;
  worker_id: string;
  node_id: string;
  status: 'PROCESSING' | 'COMPLETED' | 'PAUSED' | 'WAITING';
  row_count: number;
  throughput_label: string;
}

export interface MigrationResourcesDTO {
  attribution_is_partial: boolean;
  attributed_cpu_pct: number;
  attributed_memory_mb: number;
  attributed_network_mbps: number;
  attributed_storage_mb: number;
  host_cpu_pct: number;
  host_memory_mb: number;
  assigned_nodes: AssignedNodeItem[];
  assigned_partitions: AssignedPartitionItem[];
}

/** ========================================================================= */
/** 7. AREA 5: HEALTH & DEPENDENCIES                                          */
/** ========================================================================= */

export interface ComposedStateItem {
  dimension: string;
  state_label: string;
  is_nominal: boolean;
  detail: string;
}

export interface EndpointHealthDTO {
  endpoint_type: 'SOURCE' | 'TARGET';
  provider: string;
  instance: string;
  driver_status: string;
  reachability: 'REACHABLE' | 'UNREACHABLE' | 'DEGRADED';
  auth_status: 'AUTHORIZED' | 'UNAUTHORIZED';
  pool_active_connections: number;
  pool_max_connections: number;
  rtt_latency_ms: number;
  health: HealthState;
}

export interface ExternalDependencyItem {
  id: string;
  name: string;
  category: 'MESSAGE_BROKER' | 'STATE_STORE' | 'STORAGE_BUCKET' | 'KEY_MANAGEMENT' | 'REGISTRY';
  is_configured: boolean;
  is_applicable: boolean;
  health: HealthState;
  summary: string;
}

export interface MigrationHealthDTO {
  composed_states: ComposedStateItem[];
  source_endpoint: EndpointHealthDTO;
  target_endpoint: EndpointHealthDTO;
  runtime_workers_health: HealthState;
  wal_checkpoints_health: HealthState;
  external_dependencies: ExternalDependencyItem[];
}

/** ========================================================================= */
/** 8. AREA 6: RELIABILITY & RECOVERY                                         */
/** ========================================================================= */

export interface FailureEventItem {
  id: string;
  timestamp: string;
  error_code: string;
  stage: string;
  message: string;
  component: string;
  is_recoverable: boolean;
}

export interface CheckpointInfo {
  last_checkpoint_timestamp: string;
  generation_number: number;
  checkpoint_offset_label: string;
  storage_integrity_state: 'VERIFIED' | 'COMPROMISED' | 'PENDING';
  cas_lease_valid: boolean;
  durability_mode: string;
}

export interface RcaCandidateHypothesis {
  rank: number;
  candidate_cause: string;
  confidence_percent: number;
  supporting_evidence: string;
  epistemic_status: 'ADVISORY_HYPOTHESIS' | 'CORRELATED_ANOMALY';
}

export interface MigrationReliabilityDTO {
  active_recovery: {
    is_recovering: boolean;
    current_attempt: number;
    max_attempts: number;
    recovery_stage: string;
    progress_percent?: number | null;
    resume_checkpoint_id: string;
  };
  checkpoints: CheckpointInfo;
  resilience: {
    active_leases_count: number;
    fencing_status: 'ACTIVE' | 'EXPIRED' | 'UNPROTECTED';
    buffer_headroom_pct: number;
    disk_headroom_gb: number;
  };
  recent_failures: FailureEventItem[];
  rca_candidates: RcaCandidateHypothesis[];
}

/** ========================================================================= */
/** 9. AREA 7: ALERTS & INCIDENTS                                             */
/** ========================================================================= */

export interface MigrationAlertItem {
  id: string;
  alert_rule_name: string;
  severity: SeverityLevel;
  affected_component: string;
  triggered_at: string;
  status: 'FIRING' | 'ACKNOWLEDGED' | 'RESOLVED';
  summary: string;
  deep_link_route: string;
}

export interface LinkedIncidentItem {
  id: string;
  incident_title: string;
  severity: SeverityLevel;
  status: 'INVESTIGATING' | 'IDENTIFIED' | 'MONITORING' | 'RESOLVED';
  opened_at: string;
  summary: string;
  deep_link_route: string;
}

export interface MigrationAlertsDTO {
  active_alerts: MigrationAlertItem[];
  linked_incidents: LinkedIncidentItem[];
}

/** ========================================================================= */
/** 10. AREA 8: DIAGNOSTICS                                                   */
/** ========================================================================= */

export interface CorrelationContextDTO {
  tenant_id: string;
  workspace_id: string;
  project_id: string;
  migration_id: string;
  run_id: string;
  plan_fingerprint: string;
  correlation_id: string;
  trace_id?: string;
}

export interface DiagnosticEventItem {
  id: string;
  timestamp: string;
  event_type: string;
  severity: SeverityLevel;
  component: string;
  message: string;
}

export interface BoundedLogItem {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  logger: string;
  message: string;
}

export interface MigrationDiagnosticsDTO {
  correlation_context: CorrelationContextDTO;
  runtime_events: DiagnosticEventItem[];
  log_storage_mode: 'BOUNDED_RUNTIME_STORE' | 'UNAVAILABLE';
  bounded_logs: BoundedLogItem[];
  trace_support: {
    is_available: boolean;
    trace_id?: string;
    span_count?: number;
    status_label: string;
    truth_note: string;
  };
}

/** Complete Migration Detail Composite DTO */
export interface SelectedMigrationFullDTO {
  header: SelectedMigrationHeaderDTO;
  overview: MigrationOverviewDTO;
  execution: MigrationExecutionDTO;
  performance: MigrationPerformanceDTO;
  resources: MigrationResourcesDTO;
  health: MigrationHealthDTO;
  reliability: MigrationReliabilityDTO;
  alerts: MigrationAlertsDTO;
  diagnostics: MigrationDiagnosticsDTO;
}

