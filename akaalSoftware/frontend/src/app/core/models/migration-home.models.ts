export interface MigrationHomeRow {
  id: string;
  name: string;
  source_provider: string;
  source_label: string;
  target_provider: string;
  target_label: string;
  mode: any;
  lifecycle_state: any;
  current_stage: string;
  progress_percent: number;
  throughput_rows_per_sec?: number;
  cdc_lag_ms?: number;
  objects_completed?: number;
  objects_total?: number;
  state_sync_percent?: number;
  difference_count?: number;
  incremental_watermark?: string;
  attention_level?: string;
  attention_text?: string;
  project_id?: string;
  started_at: string;
  scheduled_at?: string;
  updated_at: string;
}

export interface ProjectHomeRow {
  id: string;
  name: string;
  environment: string;
  health: 'HEALTHY' | 'ATTENTION' | 'CRITICAL' | string;
  migration_count: number;
  active_count: number;
  attention_count: number;
  scheduled_count: number;
  delivery_percent: number;
  target_date?: string;
  owner: string;
  updated_at: string;
}

export interface ActivityHomeRow {
  id: string;
  activity_type: 'approval' | 'validation' | 'governance' | 'execution' | 'cutover' | 'recovery' | 'project' | string;
  title: string;
  subject_type: 'migration' | 'validation' | 'project' | 'history' | string;
  subject_id: string;
  subject_name: string;
  status_text: string;
  occurred_at: string;
  action_type: 'VIEW' | 'REVIEW' | 'OPEN' | string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' | string;
}

export interface MigrationHomeSummary {
  active_count: number;
  attention_count: number;
  scheduled_count: number;
  completed_count: number;
  total_count: number;
  dynamic_headline: string;
}
