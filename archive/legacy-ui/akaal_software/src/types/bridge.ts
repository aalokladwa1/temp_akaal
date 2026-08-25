/**
 * AKAAL Engine Bridge DTO Interfaces
 */

export type BridgeState =
  | 'disconnected'
  | 'starting'
  | 'connected'
  | 'reconnecting'
  | 'stopping'
  | 'stopped'
  | 'error';

export interface BridgeStatusDTO {
  state: BridgeState;
  enginePid?: number;
  activeSessionId?: string;
  transportType: string;
  heartbeatOk: boolean;
  uptimeSeconds: number;
  registeredCapabilitiesCount: number;
}

export interface CapabilityDTO {
  id: string;
  name: string;
  category: string;
  description: string;
  version: string;
  isAvailable: boolean;
}

export interface HeartbeatStatusDTO {
  isHealthy: boolean;
  lastPulseTimestamp: number;
  missedPulses: number;
  latencyMs: number;
  reconnectActive: boolean;
}

export interface RuntimeSnapshotDTO {
  migration_id: string;
  operation_id?: string | null;
  runtime_session_id?: string;
  project_id?: string;
  current_stage?: string | null;
  previous_stage?: string | null;
  next_stage?: string | null;
  current_activity?: string;
  health_status?: string;
  approval_status?: string;
  current_table?: string | null;
  current_object?: string | null;
  current_batch?: number;
  total_batches?: number;
  current_checkpoint_lsn?: string | null;
  rows_transferred?: number | null;
  rows_total?: number | null;
  rows_migrated?: number | null;
  progress_percent?: number | null;
  throughput_mbps?: number | null;
  rows_per_sec?: number | null;
  bandwidth?: string | null;
  ring_buffer?: string | null;
  wal_buffer_lag?: string | null;
  wal_lag?: string | null;
  eta_seconds?: number | null;
  elapsed_seconds?: number | null;
  duration_sec?: number | null;
  active_workers?: number;
  pid?: number | null;
  cpu_percent?: number | null;
  ram_used_gb?: number | null;
  failed_stage?: string | null;
  failed_object?: string | null;
  failed_schema?: string | null;
  error_message?: string | null;
  completed_tables?: number | null;
  total_tables?: number | null;
  indexes_built?: number | null;
  indexes_total?: number | null;
  constraints_verified?: number | null;
  lock_conflicts?: number | null;
  cdc_sync_lag_ms?: number | null;
  worker_statuses?: any[];
  warnings?: string[];
  errors?: string[];
  logs?: any[];
  available_actions?: string[];
  status?: string;
  runtime_status?: string;
  runtime_state?: string;
  stages?: any[];
}
