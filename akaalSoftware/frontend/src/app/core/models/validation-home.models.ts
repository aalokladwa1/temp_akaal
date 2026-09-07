export type ValidationStrategy =
  | 'Sync'
  | 'Async'
  | 'Structural'
  | 'Cardinality'
  | 'Partition Fingerprint'
  | 'Complete Attribute'
  | string;

export type ValidationOutcome =
  | 'Validated'
  | 'Discrepancies Found'
  | 'Execution Failed'
  | 'Cancelled'
  | 'Running'
  | 'Scheduled'
  | string;

export interface ValidationItemRow {
  id: string;
  name: string;
  source_provider: string;
  source_label?: string;
  target_provider: string;
  target_label?: string;
  strategy: ValidationStrategy;
  state: 'ACTIVE' | 'RUNNING' | 'ATTENTION' | 'SCHEDULED' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | string;
  outcome?: ValidationOutcome;
  last_run?: string;
  next_run?: string;
  progress_percent?: number;
  discrepancy_count?: number;
  elapsed_time?: string;
  owner?: string;
  description?: string;
}

export interface ValidationAttentionItem {
  id: string;
  validation_id: string;
  validation_name: string;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'HIGH' | 'WARNING' | 'INFO' | string;
  action_label: string;
  action_route: string;
  created_at: string;
}

export interface ValidationUpcomingRow {
  id: string;
  name: string;
  source_provider: string;
  target_provider: string;
  strategy: ValidationStrategy;
  next_run: string;
  schedule_state: 'ACTIVE' | 'PAUSED' | 'SCHEDULED' | string;
}

export interface ValidationRecentResultRow {
  id: string;
  validation_id: string;
  name: string;
  source_provider: string;
  target_provider: string;
  outcome: ValidationOutcome;
  completed_at: string;
  discrepancies?: number;
}

export interface ValidationActivityRow {
  id: string;
  title: string;
  validation_id: string;
  validation_name: string;
  status_text: string;
  occurred_at: string;
  action_type: 'VIEW' | 'REVIEW' | 'OPEN' | string;
  severity: 'SUCCESS' | 'WARNING' | 'ERROR' | 'INFO' | string;
}

export interface ValidationHomeSummary {
  active_count: number;
  attention_count: number;
  scheduled_count: number;
  completed_count: number;
  total_count: number;
}
