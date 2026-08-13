/**
 * AKAAL P1.3 Canonical Live Monitoring DTO Interface Contract
 */

export interface MonitoringRuntimeDTO {
  session_id: string | null;
  project_id: string;
  status: string;
  current_stage: string | null;
  health_status: string;
  approval_status: string;
  pid: number | null;
  available_actions: string[];
}

export interface MonitoringProgressDTO {
  current_table: string | null;
  current_batch: number;
  total_batches: number;
  rows_transferred: number | null;
  rows_total: number | null;
  progress_percent: number | null;
  completed_tables: number;
  total_tables: number;
}

export interface MonitoringThroughputDTO {
  rows_per_sec: number | null;
  throughput_mbps: number | null;
  bandwidth_formatted: string | null;
  eta_seconds: number | null;
}

export interface MonitoringWorkerStatusDTO {
  worker_id: string;
  status: string;
  partition_id?: string;
  rows_processed?: number;
}

export interface MonitoringWorkersDTO {
  configured_workers: number;
  active_workers: number;
  idle_workers: number;
  failed_workers: number;
  worker_statuses: MonitoringWorkerStatusDTO[];
}

export interface MonitoringBatchingDTO {
  current_batch_size: number;
  recommended_batch_size: number;
  fetch_size: number;
  batch_latency_ms: number | null;
}

export interface MonitoringConnectionsDTO {
  source_pool_size: number;
  source_pool_in_use: number;
  target_pool_size: number;
  target_pool_in_use: number;
}

export interface MonitoringCheckpointsDTO {
  current_checkpoint_id: string | null;
  last_committed_key: string | number | null;
  last_checkpoint_time: string | null;
}

export interface MonitoringRetriesDTO {
  retry_count: number;
  transient_failures: number;
  permanent_failures: number;
  last_retry_reason: string | null;
}

export interface MonitoringBackpressureDTO {
  queue_depth: number;
  queue_capacity: number;
  backpressure_state: string;
  throttle_delay_sec: number;
}

export interface MonitoringResourcesDTO {
  cpu_percent: number | null;
  ram_used_gb: number | null;
  wal_lag: string | null;
}

export interface MonitoringPartitionsDTO {
  partitions_total: number;
  partitions_active: number;
  partitions_completed: number;
}

export interface MonitoringLobDTO {
  lob_bytes_processed: number;
  lob_chunks_processed: number;
}

export interface MonitoringValidationDTO {
  validation_status: string;
  matched_rows: number | null;
  mismatched_rows: number | null;
}

export interface MonitoringCdcDTO {
  cdc_status: string;
  cdc_lag_ms: number | null;
  cdc_events_processed: number | null;
}

export interface MonitoringErrorsDTO {
  failed_stage: string | null;
  failed_object: string | null;
  failed_schema: string | null;
  error_code: string | null;
  error_message: string | null;
  errors_list: string[];
  logs_sample: any[];
}

export interface CanonicalMonitoringSnapshotDTO {
  schema_version: string;
  migration_id: string;
  captured_at: string;
  runtime: MonitoringRuntimeDTO;
  progress: MonitoringProgressDTO;
  throughput: MonitoringThroughputDTO;
  workers: MonitoringWorkersDTO;
  batching: MonitoringBatchingDTO;
  connections: MonitoringConnectionsDTO;
  checkpoints: MonitoringCheckpointsDTO;
  retries: MonitoringRetriesDTO;
  backpressure: MonitoringBackpressureDTO;
  resources: MonitoringResourcesDTO;
  partitions: MonitoringPartitionsDTO;
  lob: MonitoringLobDTO;
  validation: MonitoringValidationDTO;
  cdc: MonitoringCdcDTO;
  errors: MonitoringErrorsDTO;
}
