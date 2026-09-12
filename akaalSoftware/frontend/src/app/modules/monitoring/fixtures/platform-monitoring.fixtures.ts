/**
 * AKAAL Monitoring — Part 3 of 4: Platform Operations Fixtures
 * Truthful, realistic baseline datasets representing AKAAL internal runtime services,
 * multi-engine connectors, compute nodes, worker assignments, capacity, performance, reliability, and diagnostics.
 */

import { PlatformOperationsDTO } from '../models/platform-monitoring.models';

export const MOCK_PLATFORM_OPERATIONS: PlatformOperationsDTO = {
  summary: {
    overall_health: 'HEALTHY',
    liveness_state: 'ALIVE',
    readiness_state: 'READY',
    observed_at: new Date().toISOString(),
    freshness: 'CURRENT',
    telemetry_confidence: 'HIGH',
    active_alerts_count: 1,
    unresolved_incidents_count: 0,
    total_nodes: 4,
    healthy_nodes: 4,
    total_services: 8,
    healthy_services: 8,
    total_connectors: 12,
    healthy_connectors: 11,
    total_workers: 16,
    active_workers: 11,
    cpu_headroom_pct: 62.4,
    memory_headroom_mb: 24576
  },

  conditions: [
    {
      id: 'cond-01',
      title: 'PostgreSQL Target Connection Pool Nearing 80% Threshold',
      subsystem: 'CONNECTIVITY',
      severity: 'WARNING',
      summary: 'Connection pool on pg-aurora-cluster-prod is at 24/32 active connections during high CDC catchup burst.',
      evidence: 'Pool saturation 75% for >15 minutes; worker lease queue intact.',
      timestamp: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
      target_tab: 'connectivity'
    },
    {
      id: 'cond-02',
      title: 'Spool Disk Consumption Elevated on Worker Node 02',
      subsystem: 'CAPACITY',
      severity: 'INFO',
      summary: 'Local ring buffer spillover active on node-akaal-worker-02 (2.4 GB allocated).',
      evidence: 'WAL spillover nominal; purge cadence running every 5 minutes.',
      timestamp: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
      target_tab: 'capacity'
    }
  ],

  runtime_services: [
    {
      id: 'svc-core-gateway',
      name: 'Engine Gateway & IPC Dispatcher',
      subsystem: 'akaalEngine.gateway',
      role: 'Northbound IPC serialization, request dispatch & backpressure management',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 99.99,
      p95_latency_ms: 1.4,
      error_count_24h: 0,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'akaalIPC • CentralAuthorizationEngine',
      last_heartbeat: new Date(Date.now() - 1000 * 4).toISOString(),
      description: 'Zero-copy IPC ring buffer handling command dispatch between UI shell and Go/Python engine kernels.',
      memory_allocated_mb: 245,
      goroutines_or_threads: 48
    },
    {
      id: 'svc-coordinator',
      name: 'Pipeline Execution Coordinator',
      subsystem: 'akaalPipeline.orchestration',
      role: 'DAG stage progression, worker assignment & state machine lifecycle',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 100.0,
      p95_latency_ms: 2.8,
      error_count_24h: 0,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'RaftQuorum • CheckpointStore',
      last_heartbeat: new Date(Date.now() - 1000 * 3).toISOString(),
      description: 'Canonical orchestration authority supervising partition concurrency and atomic migration stage transitions.',
      memory_allocated_mb: 412,
      goroutines_or_threads: 64
    },
    {
      id: 'svc-checkpoint-durability',
      name: 'Checkpoint & WAL Durability Engine',
      subsystem: 'akaalEngine.durability',
      role: 'Atomic snapshotting, SCN/LSN checkpoint verification & CAS fencing',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 99.99,
      p95_latency_ms: 4.2,
      error_count_24h: 0,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'DistributedStateStore • RocksDB Local Cache',
      last_heartbeat: new Date(Date.now() - 1000 * 2).toISOString(),
      description: 'Maintains tamper-evident checkpoint commits with fencing token generation to prevent split-brain execution.',
      memory_allocated_mb: 680,
      goroutines_or_threads: 32
    },
    {
      id: 'svc-cdc-streamers',
      name: 'CDC Continuous Ingestion Daemon',
      subsystem: 'akaalEngine.cdc',
      role: 'LogMiner, Binlog & WAL2JSON stream parsing with zero-copy ring buffers',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 99.98,
      p95_latency_ms: 6.1,
      error_count_24h: 1,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'SourceDatabaseEndpoints • RingBuffer',
      last_heartbeat: new Date(Date.now() - 1000 * 5).toISOString(),
      description: 'High-throughput change capture daemon reading source transaction logs into memory-mapped change batches.',
      memory_allocated_mb: 890,
      goroutines_or_threads: 96
    },
    {
      id: 'svc-central-authz',
      name: 'Zero-Trust Central Authorization Engine',
      subsystem: 'akaalPipeline.security',
      role: 'RBAC, ABAC, SoD verification & high-assurance session gating',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 100.0,
      p95_latency_ms: 0.8,
      error_count_24h: 0,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'SessionManager • KeyStoreAuthority',
      last_heartbeat: new Date(Date.now() - 1000 * 1).toISOString(),
      description: 'Fail-closed authorization boundary verifying cryptographically signed actor context on every northbound command.',
      memory_allocated_mb: 180,
      goroutines_or_threads: 16
    },
    {
      id: 'svc-schema-engine',
      name: 'Schema Mapping & DDL Transpiler',
      subsystem: 'akaalEngine.schema',
      role: 'Cross-dialect AST schema conversion, type mapping & constraint validation',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 100.0,
      p95_latency_ms: 8.5,
      error_count_24h: 0,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'SchemaRegistry • TypeMatrix',
      last_heartbeat: new Date(Date.now() - 1000 * 6).toISOString(),
      description: 'Compiles source DDL AST into target-native optimized schemas with automatic collation and constraint translation.',
      memory_allocated_mb: 320,
      goroutines_or_threads: 24
    },
    {
      id: 'svc-validation-reconciliation',
      name: 'M8 Validation & Reconciliation Engine',
      subsystem: 'akaalEngine.validation',
      role: 'Non-mutating verification, cryptographic hash sampling & row reconciliation',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 100.0,
      p95_latency_ms: 5.4,
      error_count_24h: 0,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'EvidenceRegistry • MerkleTreeHasher',
      last_heartbeat: new Date(Date.now() - 1000 * 4).toISOString(),
      description: 'Executes parallel point-in-time and stream reconciliation probes with zero mutating effects on endpoints.',
      memory_allocated_mb: 510,
      goroutines_or_threads: 40
    },
    {
      id: 'svc-telemetry-collector',
      name: 'Platform Observability & Metrics Exporter',
      subsystem: 'akaalPipeline.observability',
      role: 'Aggregation of work rates, latencies, resource pressure & OpenTelemetry export',
      status: 'ACTIVE',
      health: 'HEALTHY',
      availability_pct: 99.99,
      p95_latency_ms: 1.1,
      error_count_24h: 0,
      version: 'v2.4.1',
      liveness: 'PASS',
      readiness: 'PASS',
      dependencies_summary: 'OpenTelemetryCollector • PrometheusRegistry',
      last_heartbeat: new Date(Date.now() - 1000 * 2).toISOString(),
      description: 'Collects sub-second telemetry across all nodes and worker pipelines, maintaining bounded 1-hour ring buffers.',
      memory_allocated_mb: 210,
      goroutines_or_threads: 20
    }
  ],

  connectors: [
    {
      id: 'conn-01',
      provider: 'Oracle DB (LogMiner & Direct Read)',
      family: 'RELATIONAL',
      driver_status: 'AUTHENTICATED',
      reachability: 'REACHABLE',
      health: 'HEALTHY',
      active_connections: 8,
      pool_max: 24,
      rtt_latency_ms: 4.2,
      endpoint_target: 'oracle-prod-core-01.bank.internal:1521/COREDB',
      tls_enabled: true,
      notes: 'DBMS_LOGMNR supplemental logging enabled.'
    },
    {
      id: 'conn-02',
      provider: 'PostgreSQL (Aurora Cluster)',
      family: 'RELATIONAL',
      driver_status: 'AUTHENTICATED',
      reachability: 'DEGRADED',
      health: 'DEGRADED',
      active_connections: 24,
      pool_max: 32,
      rtt_latency_ms: 8.5,
      endpoint_target: 'pg-aurora-cluster-prod.aws.internal:5432/ledger',
      tls_enabled: true,
      notes: 'Connection pool near 75% capacity due to high batch load.'
    },
    {
      id: 'conn-03',
      provider: 'Snowflake Enterprise Data Lake',
      family: 'WAREHOUSE',
      driver_status: 'AUTHENTICATED',
      reachability: 'REACHABLE',
      health: 'HEALTHY',
      active_connections: 6,
      pool_max: 16,
      rtt_latency_ms: 22.0,
      endpoint_target: 'xy12345.us-east-1.snowflakecomputing.com',
      tls_enabled: true,
      notes: 'Multi-cluster warehouse stage active.'
    },
    {
      id: 'conn-04',
      provider: 'Apache Kafka Event Hub',
      family: 'STREAMING',
      driver_status: 'AUTHENTICATED',
      reachability: 'REACHABLE',
      health: 'HEALTHY',
      active_connections: 12,
      pool_max: 30,
      rtt_latency_ms: 2.1,
      endpoint_target: 'kafka-cluster.prod.internal:9092',
      tls_enabled: true,
      notes: 'SASL_SSL SCRAM-SHA-512 authenticated.'
    },
    {
      id: 'conn-05',
      provider: 'Amazon S3 Object Store',
      family: 'OBJECT_STORAGE',
      driver_status: 'AUTHENTICATED',
      reachability: 'REACHABLE',
      health: 'HEALTHY',
      active_connections: 16,
      pool_max: 50,
      rtt_latency_ms: 14.2,
      endpoint_target: 's3.us-east-1.amazonaws.com/akaal-lakehouse-vault',
      tls_enabled: true,
      notes: 'SSE-KMS customer managed encryption enabled.'
    },
    {
      id: 'conn-06',
      provider: 'MongoDB Replica Set',
      family: 'NOSQL',
      driver_status: 'AUTHENTICATED',
      reachability: 'REACHABLE',
      health: 'HEALTHY',
      active_connections: 5,
      pool_max: 20,
      rtt_latency_ms: 3.8,
      endpoint_target: 'mongo-replica-01.internal:27017',
      tls_enabled: true,
      notes: 'Change stream resume tokens valid.'
    }
  ],

  external_dependencies: [
    {
      id: 'dep-01',
      name: 'Distributed State Store (RocksDB / Raft Quorum)',
      category: 'STATE_STORE',
      health: 'HEALTHY',
      reachability: 'REACHABLE • 3/3 Quorum Active',
      latency_ms: 1.2,
      summary: 'Durable metadata store for CAS leases and checkpoint offsets.'
    },
    {
      id: 'dep-02',
      name: 'Enterprise HashiCorp Vault / AWS KMS',
      category: 'KMS_VAULT',
      health: 'HEALTHY',
      reachability: 'REACHABLE • Verified Token TTL',
      latency_ms: 3.5,
      summary: 'Dynamic secret resolution with cryptographic key rotation.'
    },
    {
      id: 'dep-03',
      name: 'Schema Confluent Registry',
      category: 'SCHEMA_REGISTRY',
      health: 'HEALTHY',
      reachability: 'REACHABLE • 1,420 Schemas Cached',
      latency_ms: 2.4,
      summary: 'Avro and JSON Schema validation registry.'
    }
  ],

  nodes: [
    {
      node_id: 'node-akaal-coord-01',
      host_name: 'coord-01.us-east-1.internal',
      role: 'COORDINATOR',
      region_locality: 'us-east-1a (AWS VPC)',
      cluster_name: 'prod-primary-cluster',
      status: 'ACTIVE',
      health: 'HEALTHY',
      cpu_utilization_pct: 18.5,
      memory_used_mb: 2840,
      memory_total_mb: 16384,
      allocated_slots: 4,
      active_workers: 2,
      uptime_hours: 428,
      version: 'v2.4.1',
      last_heartbeat: new Date(Date.now() - 1000 * 2).toISOString()
    },
    {
      node_id: 'node-akaal-worker-01',
      host_name: 'worker-01.us-east-1.internal',
      role: 'WORKER_NODE',
      region_locality: 'us-east-1a (AWS VPC)',
      cluster_name: 'prod-primary-cluster',
      status: 'ACTIVE',
      health: 'HEALTHY',
      cpu_utilization_pct: 48.2,
      memory_used_mb: 6140,
      memory_total_mb: 32768,
      allocated_slots: 6,
      active_workers: 4,
      uptime_hours: 312,
      version: 'v2.4.1',
      last_heartbeat: new Date(Date.now() - 1000 * 3).toISOString()
    },
    {
      node_id: 'node-akaal-worker-02',
      host_name: 'worker-02.us-east-1.internal',
      role: 'WORKER_NODE',
      region_locality: 'us-east-1b (AWS VPC)',
      cluster_name: 'prod-primary-cluster',
      status: 'ACTIVE',
      health: 'HEALTHY',
      cpu_utilization_pct: 54.0,
      memory_used_mb: 7200,
      memory_total_mb: 32768,
      allocated_slots: 6,
      active_workers: 4,
      uptime_hours: 312,
      version: 'v2.4.1',
      last_heartbeat: new Date(Date.now() - 1000 * 4).toISOString()
    },
    {
      node_id: 'node-akaal-worker-03',
      host_name: 'worker-03.us-east-1.internal',
      role: 'PRIMARY_COMPUTE',
      region_locality: 'us-east-1c (AWS VPC)',
      cluster_name: 'prod-primary-cluster',
      status: 'ACTIVE',
      health: 'HEALTHY',
      cpu_utilization_pct: 28.5,
      memory_used_mb: 3900,
      memory_total_mb: 32768,
      allocated_slots: 6,
      active_workers: 1,
      uptime_hours: 194,
      version: 'v2.4.1',
      last_heartbeat: new Date(Date.now() - 1000 * 1).toISOString()
    }
  ],

  workers: [
    {
      worker_id: 'wrk-01-core-banking',
      node_id: 'node-akaal-worker-01',
      host_name: 'worker-01.us-east-1.internal',
      status: 'BUSY',
      health: 'HEALTHY',
      assigned_migration_id: 'mig-core-banking-01',
      assigned_migration_name: 'Core Banking Ledger Migration',
      assigned_partition: 'part_accounts_ledger_01',
      rows_processed_count: 8492048,
      work_rate_label: '24,500 ops/s',
      memory_mb: 1840,
      cpu_pct: 22.4
    },
    {
      worker_id: 'wrk-02-core-banking',
      node_id: 'node-akaal-worker-01',
      host_name: 'worker-01.us-east-1.internal',
      status: 'BUSY',
      health: 'HEALTHY',
      assigned_migration_id: 'mig-core-banking-01',
      assigned_migration_name: 'Core Banking Ledger Migration',
      assigned_partition: 'part_accounts_ledger_02',
      rows_processed_count: 7921400,
      work_rate_label: '23,800 ops/s',
      memory_mb: 1720,
      cpu_pct: 20.8
    },
    {
      worker_id: 'wrk-03-analytics',
      node_id: 'node-akaal-worker-02',
      host_name: 'worker-02.us-east-1.internal',
      status: 'BUSY',
      health: 'HEALTHY',
      assigned_migration_id: 'mig-analytics-lakehouse',
      assigned_migration_name: 'Enterprise Analytics Snapshot',
      assigned_partition: 'part_analytics_fact_orders_06',
      rows_processed_count: 14200500,
      work_rate_label: '18,200 ops/s',
      memory_mb: 2100,
      cpu_pct: 28.5
    },
    {
      worker_id: 'wrk-04-order-stream',
      node_id: 'node-akaal-worker-02',
      host_name: 'worker-02.us-east-1.internal',
      status: 'BUSY',
      health: 'HEALTHY',
      assigned_migration_id: 'mig-order-stream',
      assigned_migration_name: 'Global Order Stream Pipeline',
      assigned_partition: 'kafka_partition_0',
      rows_processed_count: 31204000,
      work_rate_label: '12,400 ops/s',
      memory_mb: 1450,
      cpu_pct: 15.2
    },
    {
      worker_id: 'wrk-05-idle-standby',
      node_id: 'node-akaal-worker-03',
      host_name: 'worker-03.us-east-1.internal',
      status: 'IDLE',
      health: 'HEALTHY',
      rows_processed_count: 0,
      work_rate_label: '0 ops/s',
      memory_mb: 320,
      cpu_pct: 1.2
    }
  ],

  leases: [
    {
      lease_id: 'lease-mig-core-banking-01',
      resource_name: 'migration:mig-core-banking-01',
      owner_node_id: 'node-akaal-coord-01',
      fencing_epoch: 42,
      lease_duration_sec: 30,
      expires_in_sec: 24,
      is_valid: true,
      state: 'ACQUIRED'
    },
    {
      lease_id: 'lease-mig-analytics-lakehouse',
      resource_name: 'migration:mig-analytics-lakehouse',
      owner_node_id: 'node-akaal-coord-01',
      fencing_epoch: 18,
      lease_duration_sec: 30,
      expires_in_sec: 21,
      is_valid: true,
      state: 'ACQUIRED'
    },
    {
      lease_id: 'lease-mig-order-stream',
      resource_name: 'migration:mig-order-stream',
      owner_node_id: 'node-akaal-coord-01',
      fencing_epoch: 64,
      lease_duration_sec: 30,
      expires_in_sec: 27,
      is_valid: true,
      state: 'ACQUIRED'
    }
  ],

  capacity: {
    cpu: {
      total_cores: 64,
      used_pct: 37.6,
      headroom_pct: 62.4,
      status: 'NORMAL'
    },
    memory: {
      total_mb: 114688, // 112 GB across cluster
      used_mb: 20080,   // ~19.6 GB
      used_pct: 17.5,
      headroom_mb: 94608,
      status: 'NORMAL'
    },
    storage_domains: [
      {
        domain: 'RocksDB Local Checkpoint Store',
        used_mb: 4820,
        capacity_mb: 50000,
        used_pct: 9.6,
        description: 'Durable local state and CAS fencing leases'
      },
      {
        domain: 'WAL & Ring Buffer Spool Disk',
        used_mb: 12400,
        capacity_mb: 100000,
        used_pct: 12.4,
        description: 'Spillover staging for high-rate CDC log batches'
      },
      {
        domain: 'Schema Artifacts & DDL Cache',
        used_mb: 320,
        capacity_mb: 10000,
        used_pct: 3.2,
        description: 'Parsed dialect ASTs and compiled execution plans'
      },
      {
        domain: 'Telemetry & Diagnostic Ring Buffer',
        used_mb: 1450,
        capacity_mb: 20000,
        used_pct: 7.2,
        description: '1-hour bounded operational telemetry metrics'
      }
    ],
    network: {
      current_ingress_mbps: 240.5,
      current_egress_mbps: 310.2,
      bandwidth_capacity_mbps: 10000.0,
      status: 'NOMINAL'
    },
    queues: {
      ring_buffer_pct: 14,
      spool_disk_pct: 12,
      backpressure_level: 'NONE'
    },
    forecasting: {
      sample_window: 'Current 60-Minute Operational Horizon',
      is_sufficient_samples: true,
      projected_exhaustion_days: null,
      advisory_notice: 'No resource exhaustion risk detected within the next 30 days under current workload velocity.'
    }
  },

  performance: {
    work_rate: {
      total_rows_per_sec: 90170,
      total_bytes_per_sec_label: '142.4 MB/s',
      total_events_per_sec: 90170,
      trend: 'stable'
    },
    latencies: {
      runtime_dispatch_ms: 1.4,
      ipc_transit_ms: 0.8,
      queue_buffer_ms: 2.2,
      sink_apply_ms: 12.5,
      p50_ms: 8.2,
      p95_ms: 18.4,
      p99_ms: 32.0
    },
    worker_skew: {
      total_workers: 11,
      balanced_workers: 10,
      elevated_workers: 1,
      stragglers: 0,
      skew_summary: 'Nominal balance across 4 cluster nodes. Worker 03 handling largest fact table chunk.'
    },
    systemic_bottlenecks: [
      {
        id: 'btn-01',
        subsystem: 'Sink Apply Pipeline (pg-aurora-cluster-prod)',
        severity: 'MEDIUM',
        description: 'Target database write batch latency at 22ms due to index update contention.',
        evidence: 'Sink apply latency accounts for 70% of total pipeline latency.'
      }
    ]
  },

  reliability: {
    failure_events: [],
    recovery_progress: {
      active_recovery_count: 0,
      successful_recoveries_24h: 3,
      failed_recoveries_24h: 0,
      current_strategy: 'Automated SCN Checkpoint Rollback & Catchup'
    },
    component_restarts: [
      {
        component: 'akaalEngine.gateway',
        restarts_24h: 0,
        uptime_duration: '17d 20h',
        churn_status: 'STABLE'
      },
      {
        component: 'akaalPipeline.orchestration',
        restarts_24h: 0,
        uptime_duration: '17d 20h',
        churn_status: 'STABLE'
      },
      {
        component: 'akaalEngine.cdc',
        restarts_24h: 0,
        uptime_duration: '13d 08h',
        churn_status: 'STABLE'
      }
    ],
    durability: {
      checkpoint_store_integrity: 'VERIFIED_NOMINAL',
      raft_consensus_state: 'QUORUM_HEALTHY',
      cas_lease_fencing_status: 'PROTECTED'
    },
    advisory_rca: [
      {
        rank: 1,
        candidate_cause: 'Target PostgreSQL WAL replication buffer saturation during peak trading hours',
        confidence_percent: 74,
        epistemic_status: 'Leading Candidate (Advisory)',
        supporting_evidence: 'Observed sink apply latency increase coinciding with target connection pool utilization reaching 24/32.'
      }
    ]
  },

  diagnostics: {
    correlation_context: {
      global_trace_id: 'trace-4a5b6c7d8e9f0a1b2c3d4e5f',
      run_id: 'run-global-platform-session-984',
      session_id: 'sess-8492048-enterprise',
      engine_fingerprint: 'sha256:7f8a9e1d2c3b4a5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e'
    },
    bounded_logs: [
      {
        id: 'log-01',
        timestamp: new Date(Date.now() - 1000 * 20).toISOString(),
        level: 'INFO',
        logger: 'akaal.platform.coordinator',
        message: 'Platform health evaluation completed. 8/8 services reporting nominal liveness and readiness.'
      },
      {
        id: 'log-02',
        timestamp: new Date(Date.now() - 1000 * 45).toISOString(),
        level: 'INFO',
        logger: 'akaal.platform.fleet',
        message: 'Node heartbeat received from node-akaal-worker-01 (4 active workers, 48.2% CPU).'
      },
      {
        id: 'log-03',
        timestamp: new Date(Date.now() - 1000 * 80).toISOString(),
        level: 'DEBUG',
        logger: 'akaal.platform.leases',
        message: 'CAS lease epoch renewed for resource migration:mig-core-banking-01 (epoch #42).'
      },
      {
        id: 'log-04',
        timestamp: new Date(Date.now() - 1000 * 120).toISOString(),
        level: 'INFO',
        logger: 'akaal.platform.durability',
        message: 'Checkpoint quorum sync verified across 3/3 Raft storage replicas.'
      },
      {
        id: 'log-05',
        timestamp: new Date(Date.now() - 1000 * 180).toISOString(),
        level: 'WARN',
        logger: 'akaal.platform.connectivity',
        message: 'Connection pool on PostgreSQL target reached 24/32 connections.'
      }
    ],
    runtime_events: [
      {
        id: 'evt-01',
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        event_type: 'CHECKPOINT_COMMITTED',
        component: 'DurabilityEngine',
        message: 'Checkpoint offset SCN 9842109824 successfully committed to Raft quorum.',
        severity: 'INFO'
      },
      {
        id: 'evt-02',
        timestamp: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
        event_type: 'WORKER_SLOT_ASSIGNED',
        component: 'Coordinator',
        message: 'Worker wrk-01-core-banking allocated slot on node-akaal-worker-01 for partition part_accounts_ledger_01.',
        severity: 'INFO'
      },
      {
        id: 'evt-03',
        timestamp: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
        event_type: 'LEASE_ACQUIRED',
        component: 'FencingAuthority',
        message: 'Distributed CAS lease acquired for migration:mig-core-banking-01 on node-akaal-coord-01.',
        severity: 'INFO'
      }
    ],
    telemetry_exporters: [
      {
        exporter_name: 'OpenTelemetry gRPC Exporter',
        protocol: 'OTLP/gRPC (v1.2)',
        status: 'ACTIVE',
        collector_endpoint: 'otel-collector.monitoring.internal:4317',
        delivery_rate_pct: 100.0
      },
      {
        exporter_name: 'Prometheus Pull Exporter',
        protocol: 'HTTP /metrics endpoint',
        status: 'ACTIVE',
        collector_endpoint: 'http://0.0.0.0:9090/metrics',
        delivery_rate_pct: 100.0
      }
    ]
  }
};
