import {
  MigrationFleetItem,
  FleetSummaryDTO,
  SelectedMigrationFullDTO
} from '../models/migration-monitoring.models';

export const MOCK_MIGRATION_FLEET: MigrationFleetItem[] = [
  {
    id: 'mig-core-banking-01',
    name: 'Core Banking Ledger Migration',
    project_id: 'proj-fintech-core',
    project_name: 'Core Banking Modernization',
    source_provider: 'Oracle DB',
    source_instance: 'oracle-prod-core-01.bank.internal',
    target_provider: 'PostgreSQL',
    target_instance: 'pg-aurora-cluster-prod.aws.internal',
    mode: 'M2_BULK_CDC',
    current_stage: 'Continuous Change Stream',
    plan_version: 'v2.4.1',
    plan_fingerprint: 'sha256:7f8a9e1d2c3b4a5e6f7a8b9c0d1e2f3a',
    operational_state: 'RUNNING',
    health: 'HEALTHY',
    progress_percent: 94,
    work_unit_label: '142.8M / 152.0M rows',
    throughput_label: '24,600 ops/s',
    lag_label: '42ms CDC lag',
    observed_at: new Date(Date.now() - 4000).toISOString(),
    freshness_state: 'CURRENT',
    attention_count: 0,
    alert_count: 0,
    deep_link_route: '/monitoring/migrations/mig-core-banking-01'
  },
  {
    id: 'mig-analytics-warehouse-02',
    name: 'Enterprise Analytics Snapshot',
    project_id: 'proj-data-platform',
    project_name: 'Enterprise Data Lakehouse',
    source_provider: 'PostgreSQL',
    source_instance: 'pg-warehouse-replica.internal',
    target_provider: 'Snowflake',
    target_instance: 'snowflake-dw-enterprise.eu-west-1',
    mode: 'M1_BULK',
    current_stage: 'Bulk Transfer (Partition 6/8)',
    plan_version: 'v1.1.0',
    plan_fingerprint: 'sha256:3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d',
    operational_state: 'RUNNING',
    health: 'HEALTHY',
    progress_percent: 75,
    work_unit_label: '3.45 TB / 4.60 TB',
    throughput_label: '185 MB/s',
    lag_label: 'N/A (Snapshot)',
    observed_at: new Date(Date.now() - 8000).toISOString(),
    freshness_state: 'CURRENT',
    attention_count: 0,
    alert_count: 0,
    deep_link_route: '/monitoring/migrations/mig-analytics-warehouse-02'
  },
  {
    id: 'mig-orders-stream-03',
    name: 'Global Order Stream Pipeline',
    project_id: 'proj-ecommerce-v2',
    project_name: 'Global Commerce Modernization',
    source_provider: 'MySQL',
    source_instance: 'mysql-orders-master.prod.internal',
    target_provider: 'Kafka Event Hub',
    target_instance: 'kafka-events-cluster.confluent.cloud',
    mode: 'M3_CDC',
    current_stage: 'Active Event Replication',
    plan_version: 'v3.0.2',
    plan_fingerprint: 'sha256:9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4e',
    operational_state: 'ACTIVE',
    health: 'HEALTHY',
    progress_percent: null, // Truthful: continuous stream has no finite percentage
    work_unit_label: '18,420 events/s',
    throughput_label: '18,420 events/s',
    lag_label: '115ms CDC lag',
    observed_at: new Date(Date.now() - 2000).toISOString(),
    freshness_state: 'CURRENT',
    attention_count: 0,
    alert_count: 0,
    deep_link_route: '/monitoring/migrations/mig-orders-stream-03'
  },
  {
    id: 'mig-customer-polling-04',
    name: 'Customer Profile Delta Sync',
    project_id: 'proj-crm-hub',
    project_name: 'Omnichannel Customer 360',
    source_provider: 'Microsoft SQL Server',
    source_instance: 'mssql-crm-prod.corp.local',
    target_provider: 'PostgreSQL',
    target_instance: 'pg-customer-identity.aws.internal',
    mode: 'M4_INCREMENTAL',
    current_stage: 'Incremental Batch (Watermark Polling)',
    plan_version: 'v1.8.4',
    plan_fingerprint: 'sha256:1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e',
    operational_state: 'ATTENTION',
    health: 'DEGRADED',
    progress_percent: 88,
    work_unit_label: '4.2M / 4.8M records',
    throughput_label: '3,200 rows/s',
    lag_label: '14m poll interval',
    observed_at: new Date(Date.now() - 15000).toISOString(),
    freshness_state: 'CURRENT',
    attention_count: 1,
    alert_count: 1,
    deep_link_route: '/monitoring/migrations/mig-customer-polling-04'
  },
  {
    id: 'mig-inventory-reconcile-05',
    name: 'Inventory State Reconciliation',
    project_id: 'proj-supply-chain',
    project_name: 'Supply Chain Sync',
    source_provider: 'DynamoDB',
    source_instance: 'dynamodb-stock-tables.us-east-1',
    target_provider: 'MongoDB',
    target_instance: 'mongodb-atlas-inventory.cluster.net',
    mode: 'M5_STATE_SYNC',
    current_stage: 'Cycle 42 Drift Resolution',
    plan_version: 'v2.0.0',
    plan_fingerprint: 'sha256:4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a',
    operational_state: 'ATTENTION',
    health: 'DEGRADED',
    progress_percent: 62,
    work_unit_label: '840 differences resolving',
    throughput_label: '950 items/s',
    lag_label: 'Drift 0.04%',
    observed_at: new Date(Date.now() - 12000).toISOString(),
    freshness_state: 'CURRENT',
    attention_count: 1,
    alert_count: 1,
    deep_link_route: '/monitoring/migrations/mig-inventory-reconcile-05'
  },
  {
    id: 'mig-billing-schema-06',
    name: 'Billing Engine Schema DDL Migration',
    project_id: 'proj-billing-nextgen',
    project_name: 'Billing Platform Modernization',
    source_provider: 'Oracle DB',
    source_instance: 'oracle-billing-master.internal',
    target_provider: 'Snowflake',
    target_instance: 'snowflake-dw-enterprise.eu-west-1',
    mode: 'M6_SCHEMA_ONLY',
    current_stage: 'DDL Verification & Constraints',
    plan_version: 'v1.0.3',
    plan_fingerprint: 'sha256:6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b',
    operational_state: 'RUNNING',
    health: 'HEALTHY',
    progress_percent: 86,
    work_unit_label: '45 / 52 DDL objects',
    throughput_label: '2.4 objects/s',
    lag_label: 'N/A (Schema)',
    observed_at: new Date(Date.now() - 6000).toISOString(),
    freshness_state: 'CURRENT',
    attention_count: 0,
    alert_count: 0,
    deep_link_route: '/monitoring/migrations/mig-billing-schema-06'
  },
  {
    id: 'mig-logs-archive-07',
    name: 'Security Logs Cold Storage Offload',
    project_id: 'proj-sec-ops',
    project_name: 'Security & Compliance Vault',
    source_provider: 'PostgreSQL',
    source_instance: 'pg-audit-archive-01.internal',
    target_provider: 'Amazon S3 Parquet',
    target_instance: 's3://corp-compliance-audit-vault',
    mode: 'M7_DATA_ONLY',
    current_stage: 'Raw Chunk Export (Table 12/16)',
    plan_version: 'v1.4.0',
    plan_fingerprint: 'sha256:8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d',
    operational_state: 'RUNNING',
    health: 'HEALTHY',
    progress_percent: 75,
    work_unit_label: '24.8M / 33.0M records',
    throughput_label: '42,000 rows/s',
    lag_label: 'N/A (Data Only)',
    observed_at: new Date(Date.now() - 9000).toISOString(),
    freshness_state: 'CURRENT',
    attention_count: 0,
    alert_count: 0,
    deep_link_route: '/monitoring/migrations/mig-logs-archive-07'
  }
];

export const MOCK_FLEET_SUMMARY: FleetSummaryDTO = {
  total_fleet_count: 7,
  active_fleet_count: 7,
  attention_fleet_count: 2,
  degraded_fleet_count: 2,
  healthy_fleet_count: 5,
  aggregated_throughput_label: '90,170 ops/s across fleet',
  observed_at: new Date().toISOString(),
  telemetry_confidence: 'CURRENT'
};

/** Default Detailed Composite Migration (M2 Bulk + CDC) */
export const MOCK_SELECTED_MIGRATION_M2: SelectedMigrationFullDTO = {
  header: {
    id: 'mig-core-banking-01',
    name: 'Core Banking Ledger Migration',
    project_id: 'proj-fintech-core',
    project_name: 'Core Banking Modernization',
    source_provider: 'Oracle DB',
    source_instance: 'oracle-prod-core-01.bank.internal',
    target_provider: 'PostgreSQL',
    target_instance: 'pg-aurora-cluster-prod.aws.internal',
    mode: 'M2_BULK_CDC',
    current_phase: 'Continuous Sync & Cutover Readiness',
    current_stage: 'Continuous Change Stream',
    plan_version: 'v2.4.1',
    plan_fingerprint: 'sha256:7f8a9e1d2c3b4a5e6f7a8b9c0d1e2f3a',
    operational_state: 'RUNNING',
    health: 'HEALTHY',
    observed_at: new Date(Date.now() - 4000).toISOString(),
    freshness_state: 'CURRENT'
  },
  overview: {
    sync_state_summary: 'Bulk initial load finished successfully. CDC replication is streaming changes with minimal lag and nominal queue saturation.',
    semantic_work_headline: '142.8M rows loaded in baseline snapshot. Current transaction stream processing 24,600 changes/sec at 42ms replication latency.',
    active_conditions: [
      {
        id: 'cond-01',
        title: 'CDC Catchup Nominal',
        detail: 'Replication lag remains under target SLA (100ms threshold, current: 42ms). All 8 pipeline workers operate within safe memory bounds.',
        severity: 'INFO',
        duration_label: 'Active for 4h 12m',
        direction: 'stable',
        action_label: 'View Replication Stream'
      },
      {
        id: 'cond-02',
        title: 'Cutover Barrier Check',
        detail: 'Target PostgreSQL database is ready for dry-run verification. 0 schema barriers detected and 0 quarantined events pending.',
        severity: 'INFO',
        duration_label: 'Evaluated 2m ago',
        direction: 'improving',
        action_label: 'Inspect Readiness Signals'
      }
    ],
    recent_events: [
      {
        id: 'evt-01',
        timestamp: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
        category: 'CDC Stream',
        summary: 'Committed log sequence offset #8492048 to checkpoint store.',
        severity: 'INFO'
      },
      {
        id: 'evt-02',
        timestamp: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
        category: 'Worker Placement',
        summary: 'Worker partition 4 rebalanced to node worker-node-02 for optimal memory affinity.',
        severity: 'INFO'
      },
      {
        id: 'evt-03',
        timestamp: new Date(Date.now() - 42 * 60 * 1000).toISOString(),
        category: 'Bulk Load',
        summary: 'Completed final bulk table chunk for LEDGER_TRANSACTIONS (42.5M rows).',
        severity: 'INFO'
      }
    ]
  },
  execution: {
    plan_info: {
      version: 'v2.4.1',
      fingerprint: 'sha256:7f8a9e1d2c3b4a5e6f7a8b9c0d1e2f3a',
      compiled_at: new Date(Date.now() - 6 * 3600 * 1000).toISOString(),
      total_nodes: 6,
      completed_nodes: 4,
      active_node_label: 'Stage 5: Continuous CDC Replication'
    },
    dag_nodes: [
      {
        id: 'dag-01',
        label: 'Pre-flight Validation & Schema Extraction',
        stage_type: 'SCHEMA',
        state: 'COMPLETED',
        progress_percent: 100,
        rows_transferred: 0,
        duration_label: '4m 18s'
      },
      {
        id: 'dag-02',
        label: 'Consistent Snapshot Lock & SCN Capture',
        stage_type: 'SNAPSHOT',
        state: 'COMPLETED',
        progress_percent: 100,
        rows_transferred: 0,
        duration_label: '1m 05s'
      },
      {
        id: 'dag-03',
        label: 'Parallel Bulk Table Data Extraction',
        stage_type: 'BULK_DATA',
        state: 'COMPLETED',
        progress_percent: 100,
        rows_transferred: 142800000,
        duration_label: '3h 12m'
      },
      {
        id: 'dag-04',
        label: 'CDC Initial Backlog Catchup',
        stage_type: 'CDC_CATCHUP',
        state: 'COMPLETED',
        progress_percent: 100,
        rows_transferred: 8450000,
        duration_label: '22m 40s'
      },
      {
        id: 'dag-05',
        label: 'Continuous Change Stream & Synchronization',
        stage_type: 'STREAM',
        state: 'RUNNING',
        progress_percent: 94,
        rows_transferred: 16200000,
        duration_label: 'Running 4h 12m'
      },
      {
        id: 'dag-06',
        label: 'Cutover Switch & Final Transaction Drain',
        stage_type: 'DRAIN',
        state: 'WAITING',
        progress_percent: 0,
        rows_transferred: 0,
        duration_label: 'Pending Operator Approval'
      }
    ],
    m2_bulk_cdc: {
      current_phase: 'CONTINUOUS_SYNC',
      bulk_rows_completed: 142800000,
      bulk_total_rows: 142800000,
      bulk_progress_pct: 100,
      cdc_replication_lag_ms: 42,
      cdc_backlog_rows: 120,
      cdc_capture_rate_per_sec: 24800,
      cdc_apply_rate_per_sec: 24600,
      cutover_readiness_signals: {
        remaining_backlog_rows: 120,
        current_lag_ms: 42,
        schema_barriers_count: 0,
        quarantined_events_count: 0,
        source_health: 'HEALTHY',
        target_health: 'HEALTHY'
      }
    }
  },
  performance: {
    work_rate_label: '24,600',
    work_rate_unit: 'ops/sec',
    work_rate_trend: 'stable',
    latencies: {
      source_read_ms: 12,
      queue_buffer_ms: 4,
      sink_apply_ms: 26,
      cdc_replication_lag_ms: 42,
      p50_ms: 38,
      p95_ms: 78,
      p99_ms: 112
    },
    flow: {
      ring_buffer_pct: 28,
      spool_disk_pct: 14,
      backpressure_level: 'NONE',
      queue_saturation_pct: 22
    },
    workers: [
      {
        id: 'wrk-01',
        name: 'Worker 01 (Partition Ledger Accounts)',
        role: 'CDC Reader & Transformer',
        assigned_partition: 'part-01-accounts',
        rows_processed: 4250000,
        rate_label: '6,200 rows/s',
        cpu_percent: 34,
        memory_mb: 512,
        skew_state: 'BALANCED'
      },
      {
        id: 'wrk-02',
        name: 'Worker 02 (Partition Ledger Transactions A)',
        role: 'CDC Stream Applier',
        assigned_partition: 'part-02-tx-a',
        rows_processed: 6100000,
        rate_label: '6,800 rows/s',
        cpu_percent: 42,
        memory_mb: 680,
        skew_state: 'BALANCED'
      },
      {
        id: 'wrk-03',
        name: 'Worker 03 (Partition Ledger Transactions B)',
        role: 'CDC Stream Applier',
        assigned_partition: 'part-03-tx-b',
        rows_processed: 5850000,
        rate_label: '6,100 rows/s',
        cpu_percent: 39,
        memory_mb: 640,
        skew_state: 'BALANCED'
      },
      {
        id: 'wrk-04',
        name: 'Worker 04 (Partition Audit Journal)',
        role: 'CDC Checkpointer',
        assigned_partition: 'part-04-journal',
        rows_processed: 5100000,
        rate_label: '5,500 rows/s',
        cpu_percent: 31,
        memory_mb: 480,
        skew_state: 'BALANCED'
      }
    ],
    bottlenecks: [
      {
        id: 'btn-01',
        subsystem: 'Target Write Buffer',
        severity: 'INFO',
        description: 'PostgreSQL batch commit throughput is balanced. Latency remains well within sub-50ms SLA.',
        trend: 'stable',
        evidence: 'Sink apply latency averaging 26ms with connection pool at 35% capacity.'
      }
    ]
  },
  resources: {
    attribution_is_partial: false,
    attributed_cpu_pct: 38,
    attributed_memory_mb: 2312,
    attributed_network_mbps: 185,
    attributed_storage_mb: 1024,
    host_cpu_pct: 44,
    host_memory_mb: 4096,
    assigned_nodes: [
      {
        node_id: 'node-compute-01',
        host_name: 'worker-node-01.prod.internal',
        region_locality: 'us-east-1a',
        slots_allocated: 4,
        active_workers: 2,
        migration_cpu_pct: 22,
        migration_memory_mb: 1192,
        health: 'HEALTHY',
        platform_route: '/monitoring/platform'
      },
      {
        node_id: 'node-compute-02',
        host_name: 'worker-node-02.prod.internal',
        region_locality: 'us-east-1b',
        slots_allocated: 4,
        active_workers: 2,
        migration_cpu_pct: 16,
        migration_memory_mb: 1120,
        health: 'HEALTHY',
        platform_route: '/monitoring/platform'
      }
    ],
    assigned_partitions: [
      {
        partition_id: 'part-01',
        partition_name: 'LEDGER_ACCOUNTS_P1',
        worker_id: 'wrk-01',
        node_id: 'node-compute-01',
        status: 'PROCESSING',
        row_count: 4250000,
        throughput_label: '6,200 rows/s'
      },
      {
        partition_id: 'part-02',
        partition_name: 'LEDGER_TRANSACTIONS_P2',
        worker_id: 'wrk-02',
        node_id: 'node-compute-01',
        status: 'PROCESSING',
        row_count: 6100000,
        throughput_label: '6,800 rows/s'
      },
      {
        partition_id: 'part-03',
        partition_name: 'LEDGER_TRANSACTIONS_P3',
        worker_id: 'wrk-03',
        node_id: 'node-compute-02',
        status: 'PROCESSING',
        row_count: 5850000,
        throughput_label: '6,100 rows/s'
      },
      {
        partition_id: 'part-04',
        partition_name: 'AUDIT_JOURNAL_P4',
        worker_id: 'wrk-04',
        node_id: 'node-compute-02',
        status: 'PROCESSING',
        row_count: 5100000,
        throughput_label: '5,500 rows/s'
      }
    ]
  },
  health: {
    composed_states: [
      {
        dimension: 'Applicability',
        state_label: 'Nominal (Configured for M2)',
        is_nominal: true,
        detail: 'Source Oracle LogMiner and target PostgreSQL logical streaming are fully applicable.'
      },
      {
        dimension: 'Configuration',
        state_label: 'Valid & Verified',
        is_nominal: true,
        detail: 'Plan parameters match runtime execution bounds without schema drift.'
      },
      {
        dimension: 'Authorization',
        state_label: 'Authenticated & Permitted',
        is_nominal: true,
        detail: 'Source SYS.DBMS_LOGMNR and target schema write permissions active.'
      },
      {
        dimension: 'Availability',
        state_label: '100% Available',
        is_nominal: true,
        detail: 'Source and target connection pools are healthy and responsive.'
      },
      {
        dimension: 'Endpoint Health',
        state_label: 'Healthy & Low Latency',
        is_nominal: true,
        detail: 'Source RTT is 4ms; target RTT is 8ms.'
      },
      {
        dimension: 'Freshness',
        state_label: 'Fresh (4s ago)',
        is_nominal: true,
        detail: 'Telemetry heartbeat received within nominal 10s poll cycle.'
      },
      {
        dimension: 'Completeness',
        state_label: 'Complete Telemetry Set',
        is_nominal: true,
        detail: 'All 8 worker metrics channels actively reporting.'
      }
    ],
    source_endpoint: {
      endpoint_type: 'SOURCE',
      provider: 'Oracle DB',
      instance: 'oracle-prod-core-01.bank.internal',
      driver_status: 'Connected (Oracle Native Driver v21.4)',
      reachability: 'REACHABLE',
      auth_status: 'AUTHORIZED',
      pool_active_connections: 8,
      pool_max_connections: 24,
      rtt_latency_ms: 4,
      health: 'HEALTHY'
    },
    target_endpoint: {
      endpoint_type: 'TARGET',
      provider: 'PostgreSQL',
      instance: 'pg-aurora-cluster-prod.aws.internal',
      driver_status: 'Connected (pgx v5.5 Pool)',
      reachability: 'REACHABLE',
      auth_status: 'AUTHORIZED',
      pool_active_connections: 12,
      pool_max_connections: 32,
      rtt_latency_ms: 8,
      health: 'HEALTHY'
    },
    runtime_workers_health: 'HEALTHY',
    wal_checkpoints_health: 'HEALTHY',
    external_dependencies: [
      {
        id: 'dep-01',
        name: 'Distributed State Store',
        category: 'STATE_STORE',
        is_configured: true,
        is_applicable: true,
        health: 'HEALTHY',
        summary: 'Embedded Raft state engine synchronized across cluster.'
      },
      {
        id: 'dep-02',
        name: 'Local Spool Storage',
        category: 'STORAGE_BUCKET',
        is_configured: true,
        is_applicable: true,
        health: 'HEALTHY',
        summary: 'NVMe fast spool drive with 480 GB free headroom.'
      }
    ]
  },
  reliability: {
    active_recovery: {
      is_recovering: false,
      current_attempt: 0,
      max_attempts: 5,
      recovery_stage: 'Idle (No active recovery required)',
      progress_percent: null,
      resume_checkpoint_id: 'chk-8492048'
    },
    checkpoints: {
      last_checkpoint_timestamp: new Date(Date.now() - 30 * 1000).toISOString(),
      generation_number: 142,
      checkpoint_offset_label: 'SCN #9842109824 / LSN 18/42A9B',
      storage_integrity_state: 'VERIFIED',
      cas_lease_valid: true,
      durability_mode: 'Synchronous Disk CAS + WAL'
    },
    resilience: {
      active_leases_count: 4,
      fencing_status: 'ACTIVE',
      buffer_headroom_pct: 72,
      disk_headroom_gb: 480
    },
    recent_failures: [],
    rca_candidates: [
      {
        rank: 1,
        candidate_cause: 'Network RTT spike on target replica cluster',
        confidence_percent: 18,
        supporting_evidence: 'Intermittent 20ms jitter detected 3 hours ago; self-resolved without worker failure.',
        epistemic_status: 'CORRELATED_ANOMALY'
      }
    ]
  },
  alerts: {
    active_alerts: [],
    linked_incidents: []
  },
  diagnostics: {
    correlation_context: {
      tenant_id: 'ten-corp-master',
      workspace_id: 'ws-fintech-prod',
      project_id: 'proj-fintech-core',
      migration_id: 'mig-core-banking-01',
      run_id: 'run-9842-live',
      plan_fingerprint: 'sha256:7f8a9e1d2c3b4a5e6f7a8b9c0d1e2f3a',
      correlation_id: 'corr-8492048-live-stream',
      trace_id: 'trace-4a5b6c7d8e9f0a1b2c3d4e5f'
    },
    runtime_events: [
      {
        id: 'diag-01',
        timestamp: new Date(Date.now() - 60 * 1000).toISOString(),
        event_type: 'CHECKPOINT_PERSISTED',
        severity: 'INFO',
        component: 'DurabilityEngine',
        message: 'Checkpoint offset SCN 9842109824 successfully committed to Raft quorum.'
      },
      {
        id: 'diag-02',
        timestamp: new Date(Date.now() - 120 * 1000).toISOString(),
        event_type: 'CDC_BATCH_APPLIED',
        severity: 'INFO',
        component: 'SinkApplier',
        message: 'Applied batch #49102 (1,200 transactions) in 24ms.'
      },
      {
        id: 'diag-03',
        timestamp: new Date(Date.now() - 240 * 1000).toISOString(),
        event_type: 'WORKER_HEARTBEAT',
        severity: 'INFO',
        component: 'WorkerCluster',
        message: 'All 4 assigned workers reported healthy heartbeats with zero memory pressure.'
      }
    ],
    log_storage_mode: 'BOUNDED_RUNTIME_STORE',
    bounded_logs: [
      {
        id: 'log-01',
        timestamp: new Date(Date.now() - 15 * 1000).toISOString(),
        level: 'INFO',
        logger: 'akaal.engine.cdc.logminer',
        message: 'Read 2,400 change events from Oracle redo log buffer sequence #8492048'
      },
      {
        id: 'log-02',
        timestamp: new Date(Date.now() - 28 * 1000).toISOString(),
        level: 'INFO',
        logger: 'akaal.engine.sink.postgres',
        message: 'Transaction commit batch applied to pg-aurora-cluster-prod in 22ms'
      },
      {
        id: 'log-03',
        timestamp: new Date(Date.now() - 45 * 1000).toISOString(),
        level: 'DEBUG',
        logger: 'akaal.engine.checkpoint',
        message: 'CAS lease heartbeat validated on key lease:migration:mig-core-banking-01'
      }
    ],
    trace_support: {
      is_available: true,
      trace_id: 'trace-4a5b6c7d8e9f0a1b2c3d4e5f',
      span_count: 48,
      status_label: 'Continuous Distributed Tracing Active',
      truth_note: 'Trace spans collected through OpenTelemetry runtime exporter.'
    }
  }
};

/** Helper to generate mode-customized details for other migrations */
export function generateSelectedMigrationDetail(fleetItem: MigrationFleetItem): SelectedMigrationFullDTO {
  // If it's our rich M2 mock, return it directly
  if (fleetItem.id === MOCK_SELECTED_MIGRATION_M2.header.id) {
    return MOCK_SELECTED_MIGRATION_M2;
  }

  // Otherwise generate custom composite matching the fleetItem's mode
  const base: SelectedMigrationFullDTO = JSON.parse(JSON.stringify(MOCK_SELECTED_MIGRATION_M2));
  base.header.id = fleetItem.id;
  base.header.name = fleetItem.name;
  base.header.project_id = fleetItem.project_id;
  base.header.project_name = fleetItem.project_name;
  base.header.source_provider = fleetItem.source_provider;
  base.header.source_instance = fleetItem.source_instance;
  base.header.target_provider = fleetItem.target_provider;
  base.header.target_instance = fleetItem.target_instance;
  base.header.mode = fleetItem.mode;
  base.header.current_stage = fleetItem.current_stage;
  base.header.plan_version = fleetItem.plan_version;
  base.header.plan_fingerprint = fleetItem.plan_fingerprint;
  base.header.operational_state = fleetItem.operational_state;
  base.header.health = fleetItem.health;

  // Clear mode objects and set the relevant one
  base.execution.m1_bulk = undefined;
  base.execution.m2_bulk_cdc = undefined;
  base.execution.m3_cdc = undefined;
  base.execution.m4_incremental = undefined;
  base.execution.m5_state_sync = undefined;
  base.execution.m6_schema = undefined;
  base.execution.m7_data_only = undefined;

  switch (fleetItem.mode) {
    case 'M1_BULK':
      base.execution.m1_bulk = {
        rows_transferred: 84500000,
        bytes_transferred: 3450000000000,
        total_rows: 112000000,
        total_bytes: 4600000000000,
        active_partitions: 6,
        total_partitions: 8,
        workers_active: 6,
        target_write_latency_ms: 18,
        checkpoint_freshness_seconds: 5
      };
      break;
    case 'M2_BULK_CDC':
      base.execution.m2_bulk_cdc = MOCK_SELECTED_MIGRATION_M2.execution.m2_bulk_cdc;
      break;
    case 'M3_CDC':
      base.execution.m3_cdc = {
        capture_rate_per_sec: 18420,
        apply_rate_per_sec: 18420,
        replication_lag_ms: 115,
        backlog_events: 420,
        backlog_bytes: 840000,
        commit_position_label: 'Offset #48920194 / Topic Partition 0',
        ring_buffer_fill_pct: 32,
        conflicts_detected: 0,
        quarantined_events: 0,
        checkpoint_freshness_sec: 3,
        ack_freshness_sec: 2
      };
      break;
    case 'M4_INCREMENTAL':
      base.execution.m4_incremental = {
        watermark_field: 'UPDATED_AT_TIMESTAMP',
        watermark_current_value: '2026-09-10T19:45:00.000Z',
        polling_cadence_seconds: 60,
        last_poll_timestamp: new Date(Date.now() - 45 * 1000).toISOString(),
        last_poll_latency_ms: 340,
        delta_rows_discovered: 3200,
        delta_rows_applied: 3200,
        batch_size: 5000,
        is_stale: false
      };
      break;
    case 'M5_STATE_SYNC':
      base.execution.m5_state_sync = {
        scan_cycle_number: 42,
        scan_duration_ms: 8400,
        entities_scanned: 185000,
        differences_discovered: 840,
        drift_detected_count: 840,
        reconciliation_backlog: 120,
        reconciliation_apply_rate_per_sec: 950,
        unresolved_differences: 120
      };
      break;
    case 'M6_SCHEMA_ONLY':
      base.execution.m6_schema = {
        objects_discovered: 52,
        objects_converted: 48,
        objects_applied: 45,
        ddl_work_rate_per_sec: 2.4,
        current_object_name: 'BILLING_INVOICE_ITEMS_FK',
        blocked_dependencies_count: 0,
        unsupported_objects_count: 0,
        manual_review_required_count: 0,
        average_ddl_latency_ms: 140
      };
      break;
    case 'M7_DATA_ONLY':
      base.execution.m7_data_only = {
        rows_transferred: 24800000,
        bytes_transferred: 18200000000,
        transfer_rate_rows_per_sec: 42000,
        active_table: 'SECURITY_AUDIT_LOG_2026',
        active_partition: 'chunk_12_of_16',
        coercion_errors_count: 0,
        target_commit_latency_ms: 14,
        spool_buffer_active: true,
        checkpoint_freshness_sec: 4
      };
      break;
  }

  return base;
}
