/**
 * AKAAL MONITORING HOME — PRODUCTION DATA MODELS (Part 1 of 4)
 * 
 * Truthful State Representation across Composed Dimensions:
 * - Applicability: APPLICABLE | NOT_APPLICABLE
 * - Configuration: CONFIGURED | NOT_CONFIGURED
 * - Authorization: AUTHORIZED | UNAUTHORIZED
 * - Availability: AVAILABLE | UNAVAILABLE
 * - Health: HEALTHY | DEGRADED | UNHEALTHY | UNKNOWN
 * - Freshness: CURRENT | STALE | NO_DATA | UNKNOWN
 * - Completeness: COMPLETE | PARTIAL
 */

export type ApplicabilityState = 'APPLICABLE' | 'NOT_APPLICABLE';
export type ConfigurationState = 'CONFIGURED' | 'NOT_CONFIGURED';
export type AuthorizationState = 'AUTHORIZED' | 'UNAUTHORIZED';
export type AvailabilityState = 'AVAILABLE' | 'UNAVAILABLE' | 'UNKNOWN';
export type HealthState = 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'UNKNOWN';
export type FreshnessState = 'CURRENT' | 'STALE' | 'NO_DATA' | 'UNKNOWN';
export type CompletenessState = 'COMPLETE' | 'PARTIAL';
export type TrendDirection = 'improving' | 'stable' | 'worsening' | 'unknown';
export type SeverityLevel = 'CRITICAL' | 'WARNING' | 'INFO' | 'UNKNOWN';

/** Canonical M1–M7 Execution Modes (M8 Validation Only is excluded from Migration Monitoring) */
export type CanonicalMigrationMode = 
  | 'M1_BULK'
  | 'M2_BULK_CDC'
  | 'M3_CDC'
  | 'M4_INCREMENTAL'
  | 'M5_STATE_SYNC'
  | 'M6_SCHEMA_ONLY'
  | 'M7_DATA_ONLY';

export interface CanonicalModeDisplay {
  code: CanonicalMigrationMode;
  tag: string;
  label: string;
  shortDescription: string;
}

export const CANONICAL_MODES: Record<CanonicalMigrationMode, CanonicalModeDisplay> = {
  M1_BULK: { code: 'M1_BULK', tag: 'M1', label: 'Bulk Snapshot', shortDescription: 'Point-in-time snapshot load' },
  M2_BULK_CDC: { code: 'M2_BULK_CDC', tag: 'M2', label: 'Bulk + CDC', shortDescription: 'Initial snapshot with continuous catchup' },
  M3_CDC: { code: 'M3_CDC', tag: 'M3', label: 'Continuous CDC', shortDescription: 'Low-latency log/stream replication' },
  M4_INCREMENTAL: { code: 'M4_INCREMENTAL', tag: 'M4', label: 'Incremental Polling', shortDescription: 'Timestamp/watermark query replication' },
  M5_STATE_SYNC: { code: 'M5_STATE_SYNC', tag: 'M5', label: 'State-Based Sync', shortDescription: 'Bi-directional/state table synchronization' },
  M6_SCHEMA_ONLY: { code: 'M6_SCHEMA_ONLY', tag: 'M6', label: 'Schema Only', shortDescription: 'DDL and structure definition migration' },
  M7_DATA_ONLY: { code: 'M7_DATA_ONLY', tag: 'M7', label: 'Data Only', shortDescription: 'Payload migration with pre-existing schema' }
};

/** Section 1: Operational Summary DTO */
export interface OperationalSummaryDTO {
  overall_platform_health: HealthState;
  telemetry_confidence: FreshnessState;
  observed_at: string; // ISO 8601 canonical timestamp
  active_migrations_count: number;
  total_migrations_count: number;
  attention_conditions_count: number;
  active_alerts_count: number;
  engine_connection_state: 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING';
  headline_message: string;
}

/** Section 3: Needs Attention Condition */
export interface NeedsAttentionCondition {
  id: string;
  entity_type: 'MIGRATION' | 'PLATFORM_RESOURCE' | 'CONNECTOR' | 'INCIDENT' | 'SECURITY';
  entity_id: string;
  entity_name: string;
  condition_title: string;
  condition_detail: string;
  severity: SeverityLevel;
  duration_label: string; // e.g., '14m', '1h 22m'
  direction: TrendDirection;
  deep_link_route: string;
  deep_link_label: string;
  is_acknowledged?: boolean;
}

/** Section 4: Active Migration Operational Summary (M1–M7) */
export interface ActiveMigrationOperationalItem {
  id: string;
  name: string;
  source_provider: string;
  source_instance: string;
  target_provider: string;
  target_instance: string;
  mode: CanonicalMigrationMode;
  current_stage: string; // From canonical ExecutionPlan DAG
  operational_state: 'ACTIVE' | 'RUNNING' | 'PAUSED' | 'ATTENTION' | 'INITIALIZING' | 'COMPLETED' | 'FAILED';
  health: HealthState;
  
  // Semantic work / progress (truthful: unknown total remains unknown, no false 0%)
  progress_percent?: number | null; // null if unknown total work
  work_unit_label?: string; // e.g. "4.2M / 10M rows" or "Stream offset 194,821"
  lag_label?: string; // e.g. "120ms lag" for CDC
  throughput_label?: string; // e.g. "42,000 rows/s"
  
  // Freshness
  observed_at: string;
  freshness_state: FreshnessState;
  
  // Route / Deep Link
  deep_link_route: string;
}

/** Section 5: Platform & Data Path Health Area */
export type PlatformAreaKey = 
  | 'SOURCES_CONNECTORS'
  | 'AKAAL_RUNTIME'
  | 'QUEUES_BUFFERS'
  | 'STORAGE'
  | 'TARGET_ENDPOINTS'
  | 'SERVICES_DEPENDENCIES';

export interface PlatformHealthArea {
  key: PlatformAreaKey;
  title: string;
  description: string;
  health: HealthState;
  active_count: number;
  total_count: number;
  degraded_summary?: string;
  deep_link_route: string;
}

/** Section 6: Operational Pressure Resource */
export type PressureResourceKey = 'CPU' | 'MEMORY' | 'STORAGE' | 'NETWORK' | 'BUFFERS_QUEUES';

export interface ResourcePressureMetric {
  key: PressureResourceKey;
  label: string;
  current_value_label: string; // e.g. "42%" or "1.8 GB / 4 GB"
  utilization_percent: number; // 0..100
  headroom_label: string; // e.g. "58% headroom"
  trend: TrendDirection;
  health: HealthState;
  threshold_warning_percent: number;
  threshold_critical_percent: number;
}

/** Section 7: Incident & Alert Item */
export interface MonitoringAlertItem {
  id: string;
  alert_rule_name: string;
  severity: SeverityLevel;
  affected_entity: string;
  entity_type: 'MIGRATION' | 'PLATFORM' | 'CONNECTOR' | 'SYSTEM';
  summary: string;
  triggered_at: string; // ISO 8601
  status: 'FIRING' | 'ACKNOWLEDGED' | 'RESOLVED';
  deep_link_route: string;
}

/** Section 8: Recent Operational Event Item */
export type OperationalEventCategory = 
  | 'STAGE_TRANSITION'
  | 'DEGRADATION'
  | 'RECOVERY'
  | 'BACKLOG_CHANGE'
  | 'STATE_CHANGE'
  | 'ALERT_LIFECYCLE';

export interface OperationalEventItem {
  id: string;
  timestamp: string; // ISO 8601
  category: OperationalEventCategory;
  category_label: string;
  entity_name: string;
  summary: string;
  severity: SeverityLevel;
  deep_link_route?: string;
}

/** Complete Monitoring Home State View Model */
export interface MonitoringHomeState {
  summary: OperationalSummaryDTO;
  needs_attention: NeedsAttentionCondition[];
  active_migrations: ActiveMigrationOperationalItem[];
  platform_health: PlatformHealthArea[];
  operational_pressure: ResourcePressureMetric[];
  active_alerts: MonitoringAlertItem[];
  recent_events: OperationalEventItem[];
}

/** Utility formatter to sanitize snake_case and SCREAMING_SNAKE_CASE strings to clean Title Case */
export function formatSnakeToTitle(value: string | null | undefined): string {
  if (!value) return '';
  return value
    .toLowerCase()
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

/** Sanitize sentences by removing underscores while preserving natural case */
export function cleanSentence(value: string | null | undefined): string {
  if (!value) return '';
  return value
    .replace(/_/g, ' ')
    .replace(/\bcdc\b/gi, 'CDC')
    .replace(/\bddl\b/gi, 'DDL')
    .replace(/\bwal\b/gi, 'WAL')
    .replace(/\bipc\b/gi, 'IPC')
    .replace(/\btls\b/gi, 'TLS')
    .replace(/\bsql\b/gi, 'SQL');
}
