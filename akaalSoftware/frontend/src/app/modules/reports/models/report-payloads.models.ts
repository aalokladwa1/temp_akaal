/**
 * AKAAL Reports — Part 2: Type-Specific Report Payload Interfaces
 * Distinct domain structures for all 14 canonical report types.
 * Every report type receives unique technical sections and payload definitions.
 */

export interface MigrationReportPayload {
  kind: 'MIGRATION';
  execution_summary: {
    total_objects: number;
    completed_objects: number;
    failed_objects: number;
    skipped_objects: number;
    total_bytes: number;
    total_rows: number;
    elapsed_seconds: number;
    average_throughput_rows_sec: number;
    checkpoint_lsn_or_scn?: string;
  };
  stages: Array<{
    stage_number: number;
    stage_name: string;
    status: 'COMPLETED' | 'IN_PROGRESS' | 'FAILED' | 'SKIPPED';
    duration_seconds: number;
    transferred_rows: number;
    transferred_bytes: number;
    error_message?: string;
  }>;
  table_transfers: Array<{
    table_name: string;
    schema_name: string;
    row_count: number;
    bytes: number;
    duration_seconds: number;
    status: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS';
  }>;
  failures_and_retries: Array<{
    object_name: string;
    attempt: number;
    error_code: string;
    error_message: string;
    resolved: boolean;
    recovery_checkpoint?: string;
  }>;
}

export interface SchemaCompatibilityReportPayload {
  kind: 'SCHEMA_COMPATIBILITY';
  assessment_summary: {
    total_objects_scanned: number;
    compatible_objects: number;
    partially_compatible: number;
    incompatible_objects: number;
    unsupported_features_count: number;
    source_dialect: string;
    target_dialect: string;
  };
  object_inventory: Array<{
    object_type: string;
    source_count: number;
    target_compatible_count: number;
    requires_manual_mapping: number;
  }>;
  type_mappings: Array<{
    source_type: string;
    target_type: string;
    precision_preserved: boolean;
    notes?: string;
  }>;
  unsupported_findings: Array<{
    object_name: string;
    object_type: string;
    issue_description: string;
    remediation_guidance: string;
  }>;
  drift_findings: Array<{
    object_name: string;
    drift_type: 'MISSING_COLUMN' | 'TYPE_MISMATCH' | 'INDEX_DIFF' | 'CONSTRAINT_DIFF';
    description: string;
  }>;
}

export interface ValidationReconciliationReportPayload {
  kind: 'VALIDATION_RECONCILIATION';
  validation_scope: {
    scope_name: string;
    entities_validated: number;
    total_source_rows: number;
    total_target_rows: number;
    mismatch_rows: number;
    checksum_algorithm?: string;
  };
  count_reconciliation: Array<{
    entity_name: string;
    source_count: number;
    target_count: number;
    delta: number;
    status: 'MATCHED' | 'MISMATCHED';
  }>;
  checksum_results: Array<{
    entity_name: string;
    source_checksum: string;
    target_checksum: string;
    matched: boolean;
  }>;
  discrepancies: Array<{
    id: string;
    entity_name: string;
    primary_key_val: string;
    mismatch_type: 'MISSING_TARGET' | 'MISSING_SOURCE' | 'VALUE_MISMATCH' | 'TYPE_CAST_ERROR';
    field_name?: string;
    source_val?: string;
    target_val?: string;
  }>;
  repair_results: Array<{
    repair_id: string;
    entity_name: string;
    discrepancy_count: number;
    resolved_count: number;
    revalidation_status: 'VERIFIED' | 'FAILED' | 'PENDING';
  }>;
}

export interface DataQualityReportPayload {
  kind: 'DATA_QUALITY';
  quality_summary: {
    rules_evaluated: number;
    rules_passed: number;
    rules_failed: number;
    total_records_checked: number;
    quarantined_records: number;
  };
  rule_evaluations: Array<{
    rule_id: string;
    rule_name: string;
    entity_name: string;
    rule_type: 'NULL_CHECK' | 'FORMAT_VALIDATION' | 'RANGE_CHECK' | 'REFERENTIAL_INTEGRITY';
    violation_count: number;
    status: 'PASSED' | 'FAILED';
  }>;
  cleansing_outcomes: Array<{
    entity_name: string;
    field_name: string;
    transform_type: string;
    records_transformed: number;
  }>;
  quarantine_records: Array<{
    quarantine_id: string;
    entity_name: string;
    reason: string;
    quarantine_timestamp: string;
    status: 'QUARANTINED' | 'RELEASED' | 'DISCARDED';
  }>;
}

export interface PerformanceReportPayload {
  kind: 'PERFORMANCE';
  summary: {
    total_duration_seconds: number;
    effective_throughput_rows_sec: number;
    effective_throughput_mb_sec: number;
    total_volume_bytes: number;
    total_records: number;
  };
  stage_durations: Array<{
    stage_name: string;
    duration_seconds: number;
    percentage_of_total: number;
  }>;
  partition_throughput: Array<{
    partition_id: string;
    entity_name: string;
    row_count: number;
    duration_seconds: number;
    rows_per_second: number;
  }>;
  durable_notes: string[];
  unavailable_telemetry_notice?: string;
}

export interface CDCReportPayload {
  kind: 'CDC';
  summary: {
    capture_status: 'STREAMING' | 'PAUSED' | 'IDLE' | 'ERROR';
    apply_status: 'STREAMING' | 'LAGGING' | 'CAUGHT_UP';
    total_transactions_captured: number;
    total_transactions_applied: number;
    quarantined_events: number;
  };
  boundary_positions: Array<{
    stream_name: string;
    provider_type: 'ORACLE' | 'POSTGRESQL' | 'MYSQL' | 'KAFKA' | 'SQL_SERVER';
    position_label: string; // e.g. "SCN", "LSN", "GTID", "Offset"
    current_position: string;
    committed_position: string;
    lag_records: number;
  }>;
  transaction_totals: Array<{
    operation: 'INSERT' | 'UPDATE' | 'DELETE' | 'DDL';
    count: number;
  }>;
  conflicts_and_quarantine: Array<{
    event_id: string;
    table_name: string;
    conflict_type: 'DUPLICATE_KEY' | 'ROW_NOT_FOUND' | 'SCHEMA_MISMATCH';
    position: string;
    occurred_at: string;
    status: 'QUARANTINED' | 'RESOLVED' | 'SKIPPED';
  }>;
}

export interface CutoverFailbackReportPayload {
  kind: 'CUTOVER_FAILBACK';
  cutover_summary: {
    decision_state: 'APPROVED' | 'READY_FOR_CUTOVER' | 'IN_PROGRESS' | 'ABORTED' | 'COMPLETED';
    final_catchup_lag_seconds: number;
    readiness_score_or_status: string;
    operator_in_charge: string;
  };
  readiness_evidence: Array<{
    check_item: string;
    category: 'CDC_DRAIN' | 'SCHEMA_VERIFICATION' | 'PERMISSION_GUARD' | 'BACKUP_CONFIRMATION';
    status: 'SATISFIED' | 'BLOCKED' | 'PENDING';
    verified_at?: string;
  }>;
  approval_gates: Array<{
    gate_name: string;
    approver_role: string;
    decision: 'APPROVED' | 'REJECTED' | 'PENDING';
    decided_at?: string;
    decision_notes?: string;
  }>;
  transition_milestones: Array<{
    timestamp: string;
    milestone: string;
    status: 'COMPLETED' | 'IN_PROGRESS' | 'FAILED';
  }>;
  failback_readiness: {
    reverse_cdc_stream_configured: boolean;
    target_snapshot_available: boolean;
    failback_procedure_status: string;
  };
}

export interface RecoveryReliabilityReportPayload {
  kind: 'RECOVERY_RELIABILITY';
  recovery_summary: {
    total_failures_encountered: number;
    automatic_restarts: number;
    manual_interventions: number;
    last_known_checkpoint: string;
  };
  failure_events: Array<{
    event_id: string;
    component: string;
    failure_type: string;
    occurred_at: string;
    recovery_action: string;
    recovered_at?: string;
    resolution_status: 'RESOLVED' | 'UNRESOLVED';
  }>;
  checkpoint_history: Array<{
    checkpoint_id: string;
    timestamp: string;
    reconstructed_state_byte_size: number;
    durable_reference: string;
  }>;
  lease_and_fencing_evidence: Array<{
    worker_node_id: string;
    lease_acquired_at: string;
    lease_fenced_at?: string;
    fencing_reason?: string;
  }>;
}

export interface SecurityReportPayload {
  kind: 'SECURITY';
  security_scope: {
    audit_scope_name: string;
    total_access_evaluations: number;
    denied_operations_count: number;
    active_identity_sessions: number;
  };
  authorization_activity: Array<{
    timestamp: string;
    principal: string;
    action: string;
    resource: string;
    decision: 'ALLOW' | 'DENY';
    policy_name: string;
  }>;
  denied_operations: Array<{
    timestamp: string;
    principal: string;
    attempted_action: string;
    resource: string;
    denial_reason: string;
  }>;
  identity_and_session_findings: Array<{
    finding_id: string;
    severity: 'HIGH' | 'MEDIUM' | 'LOW';
    description: string;
    affected_identity: string;
  }>;
  transport_security_evidence: Array<{
    endpoint: string;
    tls_version: string;
    certificate_subject: string;
    valid_until: string;
  }>;
}

export interface ComplianceReportPayload {
  kind: 'COMPLIANCE';
  compliance_scope: {
    framework_mapping_name: string;
    controls_evaluated: number;
    controls_passed: number;
    controls_with_exceptions: number;
  };
  technical_controls: Array<{
    control_id: string;
    control_name: string;
    domain: 'ACCESS_CONTROL' | 'DATA_PROTECTION' | 'INTEGRITY_VERIFICATION' | 'AUDIT_LOGGING';
    evaluation_result: 'SATISFIED' | 'EXCEPTION_RECORDED' | 'NOT_APPLICABLE';
    evidence_reference: string;
  }>;
  separation_of_duties_records: Array<{
    activity_type: string;
    operator_a: string;
    operator_b: string;
    verified_independent: boolean;
  }>;
  data_protection_evidence: Array<{
    table_or_column: string;
    masking_rule: string;
    redaction_verified: boolean;
  }>;
  exceptions: Array<{
    exception_id: string;
    control_id: string;
    description: string;
    approved_by: string;
    valid_until: string;
  }>;
}

export interface GovernanceApprovalReportPayload {
  kind: 'GOVERNANCE_APPROVAL';
  governance_summary: {
    plan_name: string;
    plan_version: string;
    barrier_status: 'CLEARED' | 'BLOCKED' | 'PENDING_APPROVAL';
    required_quorum_count: number;
    received_approvals_count: number;
  };
  approval_barriers: Array<{
    barrier_id: string;
    barrier_title: string;
    stage_locked: string;
    status: 'CLEARED' | 'ACTIVE' | 'REJECTED';
  }>;
  decision_records: Array<{
    record_id: string;
    barrier_id: string;
    approver_name: string;
    approver_role: string;
    decision: 'APPROVED' | 'REJECTED';
    decided_at: string;
    notes?: string;
  }>;
  conditions_and_expiry: Array<{
    condition_id: string;
    description: string;
    satisfied: boolean;
    expires_at?: string;
  }>;
}

export interface AuditReportPayload {
  kind: 'AUDIT';
  audit_scope: {
    time_window_start: string;
    time_window_end: string;
    total_events_recorded: number;
    privileged_actions_count: number;
    failed_operations_count: number;
  };
  records: Array<{
    timestamp: string;
    actor: string;
    action: string;
    target: string;
    result: 'SUCCESS' | 'FAILURE' | 'DENIED';
    context: string;
  }>;
  privileged_actions: Array<{
    timestamp: string;
    actor: string;
    elevated_action: string;
    justification: string;
  }>;
}

export interface InfrastructureFleetReportPayload {
  kind: 'INFRASTRUCTURE_FLEET';
  fleet_summary: {
    total_nodes: number;
    active_workers: number;
    draining_nodes: number;
    cluster_capacity_utilization_pct: number;
  };
  node_inventory: Array<{
    node_id: string;
    role: 'COORDINATOR' | 'WORKER' | 'STANDBY';
    assigned_workloads: number;
    cpu_utilization_pct: number;
    memory_utilization_pct: number;
    status: 'HEALTHY' | 'DEGRADED' | 'OFFLINE';
  }>;
  workload_placement: Array<{
    workload_id: string;
    workload_name: string;
    assigned_node: string;
    lease_status: 'ACTIVE' | 'EXPIRED' | 'FENCED';
  }>;
  historical_fleet_logs: Array<{
    timestamp: string;
    event_type: 'NODE_JOINED' | 'NODE_DRAINED' | 'WORKLOAD_REBALANCED';
    details: string;
  }>;
}

export interface ExecutiveReportPayload {
  kind: 'EXECUTIVE';
  executive_summary: {
    program_name: string;
    overall_completion_pct: number;
    readiness_status: 'ON_TRACK' | 'ATTENTION_REQUIRED' | 'BLOCKED';
    total_workloads: number;
    certified_workloads: number;
  };
  program_milestones: Array<{
    milestone_name: string;
    target_date: string;
    status: 'COMPLETED' | 'IN_PROGRESS' | 'PENDING';
    verified_reference_report_id?: string;
  }>;
  technical_domain_summaries: Array<{
    domain: string;
    status: 'SATISFIED' | 'ATTENTION' | 'PENDING';
    findings_count: number;
    linked_report_id: string;
  }>;
  risks_and_exceptions: Array<{
    risk_id: string;
    headline: string;
    severity: 'HIGH' | 'MEDIUM' | 'LOW';
    mitigation_action: string;
    linked_report_id?: string;
  }>;
}

export type ReportPayloadUnion =
  | MigrationReportPayload
  | SchemaCompatibilityReportPayload
  | ValidationReconciliationReportPayload
  | DataQualityReportPayload
  | PerformanceReportPayload
  | CDCReportPayload
  | CutoverFailbackReportPayload
  | RecoveryReliabilityReportPayload
  | SecurityReportPayload
  | ComplianceReportPayload
  | GovernanceApprovalReportPayload
  | AuditReportPayload
  | InfrastructureFleetReportPayload
  | ExecutiveReportPayload;
