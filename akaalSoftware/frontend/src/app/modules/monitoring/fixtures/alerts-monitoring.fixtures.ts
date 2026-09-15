/**
 * AKAAL Monitoring — Part 4 of 4: Alerts & Incidents Fixtures
 * Truthful, realistic baseline datasets representing Active Alerts,
 * Alert Evaluation Rules, Incidents, Signal Correlation, Notification Attempts,
 * and Operational Timeline.
 */

import { AlertsOperationsDTO } from '../models/alerts-monitoring.models';

export const MOCK_ALERTS_OPERATIONS: AlertsOperationsDTO = {
  summary: {
    total_active_alerts: 4,
    critical_alerts_count: 1,
    warning_alerts_count: 2,
    active_incidents_count: 2,
    firing_rules_count: 3,
    notification_success_rate_pct: 94.2,
    observed_at: new Date().toISOString(),
    telemetry_confidence: 'CURRENT'
  },

  alerts: [
    {
      id: 'alt-01',
      rule_id: 'rule-sink-pool-saturation',
      title: 'Target PostgreSQL Connection Pool Saturation Nearing Limit',
      signal_name: 'connector.pool.utilization_pct',
      severity: 'WARNING',
      state: 'FIRING',
      affected_entity_type: 'CONNECTOR',
      affected_entity_id: 'conn-02',
      affected_entity_name: 'PostgreSQL Aurora Target Pool (conn-02)',
      first_seen_at: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
      last_seen_at: new Date(Date.now() - 1000 * 30).toISOString(),
      recurrence_count: 14,
      dedupe_fingerprint: 'fp-pg-pool-conn-02-util75',
      linked_incident_id: 'INC-2026-0842',
      linked_incident_title: 'Aurora Connection Pool Contention During Bulk Catchup',
      telemetry_freshness: 'CURRENT',
      deep_link_platform_tab: 'connectivity',
      details: {
        rule_expression: 'conn.active_connections / conn.pool_max > 0.70 FOR 10m',
        observed_value: '24 / 32 connections (75.0%)',
        threshold_value: '70.0% utilization',
        comparator: 'GT',
        notes: 'Observed during high-velocity CDC replay stage on migration Core Banking Ledger.'
      }
    },
    {
      id: 'alt-02',
      rule_id: 'rule-cdc-stream-lag',
      title: 'CDC Continuous Ingestion Stream Lag Exceeding Threshold',
      signal_name: 'pipeline.cdc.replication_lag_ms',
      severity: 'WARNING',
      state: 'FIRING',
      affected_entity_type: 'MIGRATION',
      affected_entity_id: 'mig-core-banking-01',
      affected_entity_name: 'Core Banking Ledger Migration (M2_BULK_CDC)',
      first_seen_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
      last_seen_at: new Date(Date.now() - 1000 * 45).toISOString(),
      recurrence_count: 8,
      dedupe_fingerprint: 'fp-cdc-lag-mig-core-banking',
      linked_incident_id: 'INC-2026-0842',
      linked_incident_title: 'Aurora Connection Pool Contention During Bulk Catchup',
      telemetry_freshness: 'CURRENT',
      deep_link_migration_id: 'mig-core-banking-01',
      details: {
        rule_expression: 'stream.replication_lag_ms > 2500 FOR 5m',
        observed_value: '3,420 ms replication lag',
        threshold_value: '2,500 ms',
        comparator: 'GT',
        notes: 'Target sink database index build throttle causing temporary worker backpressure.'
      }
    },
    {
      id: 'alt-03',
      rule_id: 'rule-spool-disk-growth',
      title: 'WAL & Spool Staging Disk Growth Elevated on Worker Node 02',
      signal_name: 'node.spool_disk.used_pct',
      severity: 'INFO',
      state: 'ACKNOWLEDGED',
      affected_entity_type: 'NODE',
      affected_entity_id: 'node-akaal-worker-02',
      affected_entity_name: 'worker-02.us-east-1.internal',
      first_seen_at: new Date(Date.now() - 1000 * 60 * 75).toISOString(),
      last_seen_at: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
      recurrence_count: 22,
      dedupe_fingerprint: 'fp-node-spool-worker-02',
      linked_incident_id: null,
      telemetry_freshness: 'CURRENT',
      deep_link_platform_tab: 'infrastructure',
      details: {
        rule_expression: 'node.spool_disk_used_mb > 10000',
        observed_value: '12,400 MB (12.4% capacity)',
        threshold_value: '10,000 MB',
        comparator: 'GT',
        notes: 'Purge cadence active every 5 minutes. No immediate exhaustion risk.'
      }
    },
    {
      id: 'alt-04',
      rule_id: 'rule-sink-apply-latency',
      title: 'Sink Batch Apply P95 Latency Spike on Order Stream Target',
      signal_name: 'pipeline.stage.sink_apply.p95_ms',
      severity: 'CRITICAL',
      state: 'FIRING',
      affected_entity_type: 'MIGRATION',
      affected_entity_id: 'mig-order-stream',
      affected_entity_name: 'Global Order Stream Pipeline (M3_CDC)',
      first_seen_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
      last_seen_at: new Date(Date.now() - 1000 * 20).toISOString(),
      recurrence_count: 5,
      dedupe_fingerprint: 'fp-sink-p95-mig-order-stream',
      linked_incident_id: 'INC-2026-0841',
      linked_incident_title: 'Sink Apply Latency Degradation on Kafka Egress',
      telemetry_freshness: 'CURRENT',
      deep_link_migration_id: 'mig-order-stream',
      details: {
        rule_expression: 'sink.apply_p95_ms > 45.0 FOR 3m',
        observed_value: '58.4 ms P95 latency',
        threshold_value: '45.0 ms',
        comparator: 'GT',
        notes: 'Kafka broker partition leader rebalance detected on downstream target topic.'
      }
    }
  ],

  evaluation_rules: [
    {
      rule_id: 'rule-sink-pool-saturation',
      name: 'Connector Connection Pool Saturation High',
      signal: 'connector.pool.utilization_pct',
      observed_value: '75.0%',
      threshold_value: '70.0%',
      comparator: 'GT',
      result_state: 'FIRING',
      last_evaluated_at: new Date(Date.now() - 1000 * 15).toISOString(),
      evaluation_cadence_sec: 15,
      freshness: 'CURRENT',
      target_scope: 'CONNECTOR',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Triggers when data-path connector connection pool reaches 70% threshold.'
    },
    {
      rule_id: 'rule-cdc-stream-lag',
      name: 'CDC Continuous Ingestion Replication Lag',
      signal: 'pipeline.cdc.replication_lag_ms',
      observed_value: '3,420 ms',
      threshold_value: '2,500 ms',
      comparator: 'GT',
      result_state: 'FIRING',
      last_evaluated_at: new Date(Date.now() - 1000 * 15).toISOString(),
      evaluation_cadence_sec: 15,
      freshness: 'CURRENT',
      target_scope: 'MIGRATION',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Evaluates SCN/LSN difference between source change stream and applied target offset.'
    },
    {
      rule_id: 'rule-sink-apply-latency',
      name: 'Sink Batch Apply Latency P95',
      signal: 'pipeline.stage.sink_apply.p95_ms',
      observed_value: '58.4 ms',
      threshold_value: '45.0 ms',
      comparator: 'GT',
      result_state: 'FIRING',
      last_evaluated_at: new Date(Date.now() - 1000 * 30).toISOString(),
      evaluation_cadence_sec: 30,
      freshness: 'CURRENT',
      target_scope: 'MIGRATION',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Monitors P95 write latency against target storage and analytical endpoints.'
    },
    {
      rule_id: 'rule-spool-disk-growth',
      name: 'Worker Node Spool Disk Volume Threshold',
      signal: 'node.spool_disk.used_pct',
      observed_value: '12.4%',
      threshold_value: '10.0%',
      comparator: 'GT',
      result_state: 'NORMAL',
      last_evaluated_at: new Date(Date.now() - 1000 * 60).toISOString(),
      evaluation_cadence_sec: 60,
      freshness: 'CURRENT',
      target_scope: 'NODE',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Alerts when WAL buffer spooling on local NVMe disk exceeds standard operating threshold.'
    },
    {
      rule_id: 'rule-raft-quorum-loss',
      name: 'Distributed Raft Consensus Quorum Loss',
      signal: 'platform.raft.active_quorum_peers',
      observed_value: '3 / 3 peers',
      threshold_value: '2 peers',
      comparator: 'LT',
      result_state: 'NORMAL',
      last_evaluated_at: new Date(Date.now() - 1000 * 10).toISOString(),
      evaluation_cadence_sec: 10,
      freshness: 'CURRENT',
      target_scope: 'PLATFORM_SERVICE',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Critical platform rule triggering on loss of distributed Raft metadata quorum.'
    },
    {
      rule_id: 'rule-cas-fencing-expiry',
      name: 'CAS Lease Fencing Expiry Near Breach',
      signal: 'platform.cas.lease_expires_in_sec',
      observed_value: '24 sec',
      threshold_value: '5 sec',
      comparator: 'LT',
      result_state: 'NORMAL',
      last_evaluated_at: new Date(Date.now() - 1000 * 5).toISOString(),
      evaluation_cadence_sec: 5,
      freshness: 'CURRENT',
      target_scope: 'SYSTEM',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Monitors epoch renewal heartbeat of distributed CAS fencing tokens.'
    },
    {
      rule_id: 'rule-memory-headroom-breach',
      name: 'Cluster Global Memory Headroom Low',
      signal: 'cluster.memory.headroom_pct',
      observed_value: '82.5% free',
      threshold_value: '15.0% free',
      comparator: 'LT',
      result_state: 'NORMAL',
      last_evaluated_at: new Date(Date.now() - 1000 * 60).toISOString(),
      evaluation_cadence_sec: 60,
      freshness: 'CURRENT',
      target_scope: 'SYSTEM',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Warns when total cluster unallocated memory falls below 15% threshold.'
    },
    {
      rule_id: 'rule-authz-session-invalid',
      name: 'Central Authorization Fail-Closed Gating Rate',
      signal: 'security.authz.rejected_rate_sec',
      observed_value: '0 req/s',
      threshold_value: '5 req/s',
      comparator: 'GT',
      result_state: 'NORMAL',
      last_evaluated_at: new Date(Date.now() - 1000 * 30).toISOString(),
      evaluation_cadence_sec: 30,
      freshness: 'CURRENT',
      target_scope: 'PLATFORM_SERVICE',
      rule_owner_module: 'ADMINISTRATION',
      description: 'Detects unauthorized session token bursts across northbound IPC endpoints.'
    }
  ],

  incidents: [
    {
      id: 'INC-2026-0842',
      title: 'Aurora Connection Pool Contention During Bulk Catchup',
      severity: 'HIGH',
      status: 'INVESTIGATING',
      affected_scope_label: 'PostgreSQL Aurora (conn-02) • Core Banking (mig-01)',
      opened_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      last_updated_at: new Date(Date.now() - 1000 * 60 * 3).toISOString(),
      linked_alerts_count: 2,
      linked_alerts: [],
      affected_migration_id: 'mig-core-banking-01',
      affected_migration_name: 'Core Banking Ledger Migration',
      affected_platform_resource: 'PostgreSQL Aurora Target Pool (conn-02)',
      summary: 'Connection pool on pg-aurora-cluster-prod saturated at 24/32 connections, elevating CDC catchup latency to 3.4s.',
      advisory_rca: [
        {
          hypothesis: 'Target PostgreSQL write batch lock contention during simultaneous secondary index creation',
          confidence_pct: 78,
          epistemic_status: 'Leading Candidate (Advisory)',
          evidence: 'Observed sink apply latency increase coinciding with target connection pool utilization reaching 24/32.'
        }
      ],
      timeline: [
        {
          id: 'tl-inc-01',
          timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
          event_type: 'INCIDENT_OPENED',
          actor: 'System Autonomous Monitor',
          description: 'Incident opened automatically from alert rule-sink-pool-saturation firing on conn-02.',
          severity: 'WARNING'
        },
        {
          id: 'tl-inc-02',
          timestamp: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
          event_type: 'NOTIFICATION_DISPATCHED',
          actor: 'Dispatcher Service',
          description: 'Dispatched incident webhook to Slack #akaal-ops and PagerDuty escalation tier 1.',
          severity: 'INFO'
        },
        {
          id: 'tl-inc-03',
          timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
          event_type: 'ALERT_ATTACHED',
          actor: 'Correlation Engine',
          description: 'Correlated alert rule-cdc-stream-lag (mig-core-banking-01) attached to active incident.',
          severity: 'WARNING'
        },
        {
          id: 'tl-inc-04',
          timestamp: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
          event_type: 'ACKNOWLEDGEMENT',
          actor: 'Operator (Aalok L.)',
          description: 'Incident acknowledged. Monitoring CDC catchup buffer velocity.',
          severity: 'INFO'
        }
      ],
      operational_notes: [
        {
          id: 'note-01',
          timestamp: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
          author: 'Aalok L.',
          content: 'Target Aurora connection pool has stabilized at 24/32. WAL buffers intact; no data loss risk.'
        }
      ]
    },
    {
      id: 'INC-2026-0841',
      title: 'Sink Apply Latency Degradation on Kafka Egress',
      severity: 'CRITICAL',
      status: 'MONITORING',
      affected_scope_label: 'Apache Kafka Target (conn-04) • Global Order Stream (mig-order-stream)',
      opened_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
      last_updated_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
      linked_alerts_count: 1,
      linked_alerts: [],
      affected_migration_id: 'mig-order-stream',
      affected_migration_name: 'Global Order Stream Pipeline',
      affected_platform_resource: 'Apache Kafka Event Hub (conn-04)',
      summary: 'Sink apply latency spiked to 58.4ms due to downstream broker partition rebalancing.',
      advisory_rca: [
        {
          hypothesis: 'Kafka cluster broker node 03 offline trigger causing partition reassignment and batch TCP retries',
          confidence_pct: 86,
          epistemic_status: 'Confirmed by Telemetry Correlation',
          evidence: 'TCP retransmission rate spiked to 4.2% on port 9092 during partition leader election.'
        }
      ],
      timeline: [
        {
          id: 'tl-inc-11',
          timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
          event_type: 'INCIDENT_OPENED',
          actor: 'System Autonomous Monitor',
          description: 'Incident opened after sink batch apply P95 exceeded 45ms for 3 consecutive evaluation windows.',
          severity: 'CRITICAL'
        },
        {
          id: 'tl-inc-12',
          timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
          event_type: 'MITIGATION_APPLIED',
          actor: 'Kafka Cluster Controller',
          description: 'Partition reassignment complete; target broker leader election resolved.',
          severity: 'INFO'
        },
        {
          id: 'tl-inc-13',
          timestamp: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
          event_type: 'STATUS_CHANGED',
          actor: 'Operator (Aalok L.)',
          description: 'Status transitioned from INVESTIGATING to MONITORING following latency recovery.',
          severity: 'INFO'
        }
      ],
      operational_notes: [
        {
          id: 'note-11',
          timestamp: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
          author: 'Aalok L.',
          content: 'Broker recovered. Latency dropping back toward 18ms baseline.'
        }
      ]
    }
  ],

  correlation: {
    selected_scope_type: 'INCIDENT',
    correlation_id: 'corr-ctx-inc-2026-0842',
    trace_id: 'trc-8f92a1b7-prod-core',
    correlation_summary: 'Target DB pool saturation on conn-02 propagating backpressure to CDC streamer daemon on worker-02 and migration mig-core-banking-01.',
    signal_chain: [
      {
        level: 'Primary Signal',
        label: 'connector.pool.utilization_pct (75.0%)',
        id: 'sig-01',
        status: 'DEGRADED',
        deep_link: '/monitoring/platform/connectivity'
      },
      {
        level: 'Triggered Alert',
        label: 'alt-01: Target PostgreSQL Pool Saturation',
        id: 'alt-01',
        status: 'FIRING',
        deep_link: '/monitoring/alerts/active'
      },
      {
        level: 'Active Incident',
        label: 'INC-2026-0842: Aurora Pool Contention',
        id: 'INC-2026-0842',
        status: 'INVESTIGATING',
        deep_link: '/monitoring/alerts/incidents'
      },
      {
        level: 'Affected Workload',
        label: 'Core Banking Ledger Migration (M2_BULK_CDC)',
        id: 'mig-core-banking-01',
        status: 'RUNNING',
        deep_link: '/monitoring/migrations/mig-core-banking-01'
      },
      {
        level: 'Underlying Node',
        label: 'node-akaal-worker-02 (worker-02.us-east-1.internal)',
        id: 'node-akaal-worker-02',
        status: 'HEALTHY',
        deep_link: '/monitoring/platform/infrastructure'
      }
    ],
    related_entities: [
      {
        type: 'MIGRATION',
        name: 'Core Banking Ledger Migration',
        id: 'mig-core-banking-01',
        role: 'Active Bulk + CDC Execution',
        health: 'DEGRADED',
        deep_link: '/monitoring/migrations/mig-core-banking-01'
      },
      {
        type: 'CONNECTOR',
        name: 'PostgreSQL Aurora Target Pool',
        id: 'conn-02',
        role: 'Relational Target Sink',
        health: 'DEGRADED',
        deep_link: '/monitoring/platform/connectivity'
      },
      {
        type: 'SERVICE',
        name: 'CDC Continuous Ingestion Daemon',
        id: 'svc-cdc-streamers',
        role: 'LogMiner / WAL2JSON Parser',
        health: 'HEALTHY',
        deep_link: '/monitoring/platform/runtime'
      },
      {
        type: 'NODE',
        name: 'worker-02.us-east-1.internal',
        id: 'node-akaal-worker-02',
        role: 'Data Plane Worker Node',
        health: 'HEALTHY',
        deep_link: '/monitoring/platform/infrastructure'
      }
    ],
    related_telemetry: [
      {
        metric: 'PostgreSQL Active Connections',
        value: '24 / 32 (75%)',
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        anomaly: true
      },
      {
        metric: 'CDC Replication Lag',
        value: '3,420 ms',
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        anomaly: true
      },
      {
        metric: 'Sink Batch Write Duration',
        value: '18.4 ms',
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        anomaly: false
      },
      {
        metric: 'Spool Buffer Spillover',
        value: '2.4 GB',
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        anomaly: false
      }
    ],
    temporal_events: [
      {
        timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
        source: 'conn-02 (Aurora)',
        message: 'Connection pool utilization crossed 70% threshold (23/32).',
        severity: 'WARNING'
      },
      {
        timestamp: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
        source: 'node-akaal-worker-02',
        message: 'Local spool disk buffer spillover allocated 2.4 GB.',
        severity: 'INFO'
      },
      {
        timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
        source: 'mig-core-banking-01',
        message: 'CDC stream replication lag reached 3.4s during batch commit.',
        severity: 'WARNING'
      }
    ]
  },

  notifications: [
    {
      id: 'notif-01',
      channel_type: 'SLACK',
      channel_name: 'Slack #akaal-ops-critical',
      target_endpoint: 'https://hooks.slack.com/services/T00/B00/XXXX',
      attempt_timestamp: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
      status: 'DELIVERED',
      response_code: 200,
      latency_ms: 184,
      retry_count: 0,
      max_retries: 3,
      error_message: null,
      linked_alert_id: 'alt-01',
      linked_incident_id: 'INC-2026-0842',
      escalation_step: 1,
      escalation_policy_ref: 'POLICY-TIER-1-STANDARD',
      external_proof_status: 'VERIFIED_DELIVERY'
    },
    {
      id: 'notif-02',
      channel_type: 'PAGERDUTY',
      channel_name: 'PagerDuty On-Call Schedule',
      target_endpoint: 'https://events.pagerduty.com/v2/enqueue',
      attempt_timestamp: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
      status: 'DELIVERED',
      response_code: 202,
      latency_ms: 312,
      retry_count: 0,
      max_retries: 3,
      error_message: null,
      linked_alert_id: 'alt-01',
      linked_incident_id: 'INC-2026-0842',
      escalation_step: 1,
      escalation_policy_ref: 'POLICY-TIER-1-STANDARD',
      external_proof_status: 'VERIFIED_DELIVERY'
    },
    {
      id: 'notif-03',
      channel_type: 'WEBHOOK',
      channel_name: 'Enterprise IT Service Management (ITSM)',
      target_endpoint: 'https://itsm.internal.corp/api/v2/incidents',
      attempt_timestamp: new Date(Date.now() - 1000 * 60 * 39).toISOString(),
      status: 'RETRYING',
      response_code: 504,
      latency_ms: 5002,
      retry_count: 2,
      max_retries: 5,
      error_message: 'Gateway Timeout HTTP 504 from upstream ITSM gateway.',
      linked_alert_id: 'alt-01',
      linked_incident_id: 'INC-2026-0842',
      escalation_step: 2,
      escalation_policy_ref: 'POLICY-TIER-2-ENTERPRISE',
      external_proof_status: 'UNVERIFIED'
    },
    {
      id: 'notif-04',
      channel_type: 'EMAIL',
      channel_name: 'Platform Engineering Distribution List',
      target_endpoint: 'ops-alerts@akaal.enterprise.internal',
      attempt_timestamp: new Date(Date.now() - 1000 * 60 * 115).toISOString(),
      status: 'DELIVERED',
      response_code: 250,
      latency_ms: 92,
      retry_count: 0,
      max_retries: 3,
      error_message: null,
      linked_alert_id: 'alt-04',
      linked_incident_id: 'INC-2026-0841',
      escalation_step: 1,
      escalation_policy_ref: 'POLICY-TIER-1-STANDARD',
      external_proof_status: 'VERIFIED_DELIVERY'
    },
    {
      id: 'notif-05',
      channel_type: 'SYSTEM_LOG',
      channel_name: 'Audit & Compliance Journal Log',
      target_endpoint: 'local://var/log/akaal/notifications.journal',
      attempt_timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
      status: 'DELIVERED',
      response_code: 0,
      latency_ms: 2,
      retry_count: 0,
      max_retries: 1,
      error_message: null,
      linked_alert_id: 'alt-04',
      linked_incident_id: 'INC-2026-0841',
      escalation_step: 1,
      escalation_policy_ref: 'POLICY-AUDIT-IMMUTABLE',
      external_proof_status: 'VERIFIED_DELIVERY'
    }
  ],

  timeline: [
    {
      id: 'evt-tl-01',
      timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
      category: 'ALERT_FIRING',
      severity: 'CRITICAL',
      entity_name: 'Global Order Stream Pipeline',
      entity_type: 'MIGRATION',
      summary: 'Alert alt-04 firing: Sink apply latency P95 reached 58.4ms.',
      payload_preview: 'rule: rule-sink-apply-latency • observed: 58.4ms • threshold: 45.0ms',
      deep_link_route: '/monitoring/alerts/active'
    },
    {
      id: 'evt-tl-02',
      timestamp: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
      category: 'INCIDENT_LIFECYCLE',
      severity: 'INFO',
      entity_name: 'INC-2026-0841',
      entity_type: 'SYSTEM',
      summary: 'Status transitioned from INVESTIGATING to MONITORING by Aalok L.',
      payload_preview: 'target: Apache Kafka Event Hub (conn-04)',
      deep_link_route: '/monitoring/alerts/incidents'
    },
    {
      id: 'evt-tl-03',
      timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
      category: 'ALERT_FIRING',
      severity: 'WARNING',
      entity_name: 'Core Banking Ledger Migration',
      entity_type: 'MIGRATION',
      summary: 'Alert alt-02 firing: CDC stream replication lag reached 3,420ms.',
      payload_preview: 'rule: rule-cdc-stream-lag • threshold: 2500ms',
      deep_link_route: '/monitoring/alerts/active'
    },
    {
      id: 'evt-tl-04',
      timestamp: new Date(Date.now() - 1000 * 60 * 39).toISOString(),
      category: 'NOTIFICATION_DELIVERY',
      severity: 'WARNING',
      entity_name: 'Enterprise ITSM Webhook',
      entity_type: 'SYSTEM',
      summary: 'Notification delivery attempt failed (HTTP 504 Gateway Timeout). Retrying attempt 2/5.',
      payload_preview: 'endpoint: https://itsm.internal.corp/api/v2/incidents',
      deep_link_route: '/monitoring/alerts/notifications'
    },
    {
      id: 'evt-tl-05',
      timestamp: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
      category: 'NOTIFICATION_DELIVERY',
      severity: 'INFO',
      entity_name: 'Slack #akaal-ops-critical',
      entity_type: 'SYSTEM',
      summary: 'Notification delivered successfully (HTTP 200, 184ms).',
      payload_preview: 'linked incident: INC-2026-0842',
      deep_link_route: '/monitoring/alerts/notifications'
    },
    {
      id: 'evt-tl-06',
      timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      category: 'INCIDENT_LIFECYCLE',
      severity: 'WARNING',
      entity_name: 'INC-2026-0842',
      entity_type: 'SYSTEM',
      summary: 'Incident opened automatically: Aurora Connection Pool Contention.',
      payload_preview: 'affected: PostgreSQL Aurora Target Pool (conn-02)',
      deep_link_route: '/monitoring/alerts/incidents'
    },
    {
      id: 'evt-tl-07',
      timestamp: new Date(Date.now() - 1000 * 60 * 75).toISOString(),
      category: 'ACKNOWLEDGEMENT',
      severity: 'INFO',
      entity_name: 'worker-02.us-east-1.internal',
      entity_type: 'NODE',
      summary: 'Alert alt-03 acknowledged: WAL & Spool disk growth nominal.',
      payload_preview: 'acknowledged by system rule suppression window',
      deep_link_route: '/monitoring/alerts/active'
    },
    {
      id: 'evt-tl-08',
      timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
      category: 'INCIDENT_LIFECYCLE',
      severity: 'CRITICAL',
      entity_name: 'INC-2026-0841',
      entity_type: 'SYSTEM',
      summary: 'Incident opened: Sink Apply Latency Degradation on Kafka Egress.',
      payload_preview: 'affected: Apache Kafka Target (conn-04)',
      deep_link_route: '/monitoring/alerts/incidents'
    }
  ]
};
