/**
 * AKAAL Reports — Part 2: Reports Service
 * Signal-driven reactive store managing Reports Home, Report Library (Catalog & Inventory),
 * Selected Report envelope and all 14 type-specific payloads, contextual Export dispatch,
 * and independent section loading states.
 */

import { Injectable, signal, computed } from '@angular/core';
import { 
  ReportsHomeDataDTO,
  ReportsSummaryMetricsDTO,
  ReportItemDTO,
  CertificationAttentionItemDTO,
  EvidenceActivityItemDTO,
  SectionLoadingState,
  ReportCategoryKey,
  REPORT_CATEGORIES,
  ReportDetailEnvelopeDTO,
  ExportRequestDTO,
  ExportResponseDTO,
  ExportFormat,
  formatReportText
} from '../models/reports.models';
import { ReportPayloadUnion } from '../models/report-payloads.models';
import { 
  CertificationDetailEnvelopeDTO,
  CertificationSummaryDTO,
  CertificationExceptionDTO,
  VerificationResultDTO 
} from '../models/certification.models';
import { 
  EvidenceItemDTO,
  EvidenceDetailEnvelopeDTO,
  DossierDTO,
  CertificateArtifactDTO,
  EvidencePackageDTO,
  PackageManifestItemDTO,
  EvidencePaginationQuery,
  PaginatedResult
} from '../models/evidence.models';
import { IpcService } from '../../../core/services/ipc.service';

export type LibraryViewMode = 'CATALOG' | 'INVENTORY' | 'CATEGORY_VIEW' | 'REPORT_DETAIL';
export type CertificationViewMode = 'OVERVIEW' | 'MIGRATION' | 'VALIDATION' | 'VERIFICATION';
export type EvidenceTabMode = 'EXPLORER' | 'DOSSIERS' | 'CERTIFICATES' | 'PACKAGES' | 'VERIFICATION';

const INITIAL_CERTIFICATION_ENVELOPES: Record<string, CertificationDetailEnvelopeDTO> = {
  'CERT-MIG-2026-001': {
    id: 'CERT-MIG-2026-001',
    domain: 'MIGRATION',
    title: 'Core Banking Ledger Migration Execution Certification',
    subject_name: 'Core Banking Ledger Migration',
    subject_id: 'mig-core-banking-01',
    issued_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    producer_authority: 'MigrationAssuranceEngine',
    decision: 'CERTIFIED',
    lifecycle: 'ACTIVE',
    summary: 'Formal migration completion assertion verifying 14,200,000 transferred customer accounts with full partition savepoint integrity.',
    scope_summary: 'In-scope: 142 primary tables, 318 secondary indexes, 48 sequences across Oracle 19c to PostgreSQL 16.',
    criteria: [
      {
        id: 'crit-mig-01',
        name: 'Bulk Extraction & Partition Parity',
        required_condition: '100% of source partitions extracted and acknowledged by target worker pool.',
        observed_result: '32 of 32 partitions transferred across 14.2M records without dropped records.',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-MIG-01'
      },
      {
        id: 'crit-mig-02',
        name: 'Continuous CDC Stream Convergence',
        required_condition: 'Replication watermark lag <= 500ms over 30 consecutive sampling intervals.',
        observed_result: 'Mean lag measured at 12ms (max 48ms) prior to cutover quiesce.',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-CDC-01'
      },
      {
        id: 'crit-mig-03',
        name: 'Dual-Control Governance Approval Gate',
        required_condition: 'Stage 4 Production Gate approved by Lead DBA and Security Officer.',
        observed_result: 'Dual sign-off recorded under Change Ticket CHG-994182.',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-GOV-01'
      },
      {
        id: 'crit-mig-04',
        name: 'Dual-Engine Reconciliation Parity',
        required_condition: 'Post-migration row count and cryptographic checksum match across all tables.',
        observed_result: 'Reconciliation verified with 0 discrepancies.',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-VAL-01'
      }
    ],
    evidence: [
      {
        id: 'EV-2026-MIG-01',
        title: 'Partition Bulk Transfer Manifest',
        artifact_type: 'MANIFEST_SNAPSHOT',
        subject_name: 'Core Banking Ledger Migration',
        sha256_digest: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 50).toISOString(),
        deep_link_route: '/reports/evidence'
      },
      {
        id: 'EV-2026-VAL-01',
        title: 'Dual-Engine Validation Digest Package',
        artifact_type: 'VALIDATION_DIGEST',
        subject_name: 'Core Banking Ledger Migration',
        sha256_digest: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 48).toISOString(),
        deep_link_route: '/reports/evidence'
      },
      {
        id: 'EV-2026-GOV-01',
        title: 'Dual-Control Sign-off Ledger Record',
        artifact_type: 'GOVERNANCE_LEDGER',
        subject_name: 'Core Banking Ledger Migration',
        sha256_digest: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 46).toISOString(),
        deep_link_route: '/reports/evidence'
      }
    ],
    governance: {
      barrier_name: 'Stage 4 Production Cutover Gate',
      decision_status: 'APPROVED',
      required_quorum: 2,
      approvals_received: 2,
      required_roles: ['Lead Migration DBA', 'SecOps Officer'],
      approvers: [
        { role: 'Lead Migration DBA', actor_name: 'Marcus Vance', timestamp: new Date(Date.now() - 1000 * 60 * 55).toISOString(), decision: 'APPROVED' },
        { role: 'SecOps Officer', actor_name: 'Elena Rostova', timestamp: new Date(Date.now() - 1000 * 60 * 52).toISOString(), decision: 'APPROVED' }
      ],
      conditions: ['All validation checksums verified prior to traffic cutover', 'Standby failback replication buffer active for 48 hours']
    },
    exceptions: [],
    integrity: {
      sha256_fingerprint: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
      producer_authority: 'AKAAL Migration Assurance Service v2.4',
      verification_status: 'VERIFIED',
      verification_method: 'SHA-256 Digest Match',
      verified_at: new Date(Date.now() - 1000 * 60 * 40).toISOString()
    },
    related_report_ids: ['REP-2026-0101', 'REP-2026-0104'],
    migration_payload: {
      execution_mode: 'Bulk Extract + Continuous CDC',
      execution_outcome: 'Completed Successfully with Zero Dropped Rows',
      transferred_scope_summary: '14,200,000 rows across 142 tables (8.4 GB payload).',
      checkpoint_recovery_evidence_summary: 'Savepoint log confirmed all worker thread checkpoint markers safely committed to Postgres WAL.',
      cutover_evidence_summary: 'Cutover window completed in 04m:18s (well within SLA budget of 15m:00s).'
    }
  },
  'CERT-VAL-2026-002': {
    id: 'CERT-VAL-2026-002',
    domain: 'VALIDATION',
    title: 'Dual-Engine Reconciliation & Hash Parity Certification',
    subject_name: 'Core Banking Ledger Migration',
    subject_id: 'mig-core-banking-01',
    issued_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    producer_authority: 'ValidationAssuranceEngine',
    decision: 'CERTIFIED',
    lifecycle: 'ACTIVE',
    summary: 'Dual-engine validation attestation confirming row counts and column-level checksum parity across source Oracle and target PostgreSQL.',
    scope_summary: 'Full volumetric comparison across 142 tables in core banking ledger dataset.',
    criteria: [
      {
        id: 'crit-val-01',
        name: 'Row Count Cardinality Parity',
        required_condition: 'Delta between source and target row count must be exactly 0.',
        observed_result: 'Source count: 14,200,000 | Target count: 14,200,000 (Delta: 0).',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-VAL-01'
      },
      {
        id: 'crit-val-02',
        name: 'Block-Level SHA-256 Checksum Match',
        required_condition: 'Sampled block hashes match with zero bit-rot discrepancies.',
        observed_result: '1,000 sample blocks checked; 1,000 matches (0 mismatches).',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-VAL-01'
      },
      {
        id: 'crit-val-03',
        name: 'Primary & Foreign Key Constraint Integrity',
        required_condition: 'Zero orphaned foreign keys or duplicate primary key violations.',
        observed_result: '0 orphaned rows detected across 38 relational constraints.',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-VAL-02'
      }
    ],
    evidence: [
      {
        id: 'EV-2026-VAL-01',
        title: 'Cardinality & Merkle Tree Root Manifest',
        artifact_type: 'MERKLE_TREE_DIGEST',
        subject_name: 'Core Banking Ledger Migration',
        sha256_digest: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 65).toISOString(),
        deep_link_route: '/reports/evidence'
      },
      {
        id: 'EV-2026-VAL-02',
        title: 'Relational Constraint Scan Report',
        artifact_type: 'INTEGRITY_SCAN',
        subject_name: 'Core Banking Ledger Migration',
        sha256_digest: '8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 62).toISOString(),
        deep_link_route: '/reports/evidence'
      }
    ],
    exceptions: [],
    integrity: {
      sha256_fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      producer_authority: 'AKAAL Validation Engine v3.1',
      verification_status: 'VERIFIED',
      verification_method: 'SHA-256 Digest Match',
      verified_at: new Date(Date.now() - 1000 * 60 * 58).toISOString()
    },
    related_report_ids: ['REP-2026-0101'],
    validation_payload: {
      validation_scope_summary: '142 tables, 14,200,000 total records verified.',
      source_target_comparison_summary: 'Source: Oracle 19c Enterprise | Target: PostgreSQL 16.2 Cloud Native.',
      count_reconciliation_summary: 'Exact count equality verified across 100% of tables.',
      checksum_merkle_summary: 'Merkle root hash comparison verified with zero bit divergence.',
      discrepancies_summary: 'Zero unresolved structural or data discrepancies recorded.'
    }
  },
  'CERT-MIG-2026-003': {
    id: 'CERT-MIG-2026-003',
    domain: 'MIGRATION',
    title: 'Snowflake Data Lakehouse Batch Snapshot Certification',
    subject_name: 'Enterprise Data Lakehouse',
    subject_id: 'mig-ent-analytics',
    issued_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    producer_authority: 'MigrationAssuranceEngine',
    decision: 'CERTIFIED',
    lifecycle: 'ACTIVE',
    summary: 'Batch partition migration snapshot certified across 8 partitions representing 8.4 GB payload.',
    scope_summary: '8 partitioned analytical datasets transferred to Snowflake stage.',
    criteria: [
      {
        id: 'crit-mig-03-01',
        name: 'Parquet Serialization Conformance',
        required_condition: 'All exported chunks conform to Parquet v2 schema specification.',
        observed_result: 'All 8 partitions validated against strict schema definition.',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-MIG-03'
      }
    ],
    evidence: [
      {
        id: 'EV-2026-MIG-03',
        title: 'Snowflake Stage Ingestion Manifest',
        artifact_type: 'MANIFEST_SNAPSHOT',
        subject_name: 'Enterprise Data Lakehouse',
        sha256_digest: '3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 185).toISOString(),
        deep_link_route: '/reports/evidence'
      }
    ],
    exceptions: [],
    integrity: {
      sha256_fingerprint: '3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c',
      producer_authority: 'AKAAL Analytics Bridge v1.8',
      verification_status: 'VERIFIED',
      verification_method: 'SHA-256 Digest Match'
    },
    related_report_ids: ['REP-2026-0104'],
    migration_payload: {
      execution_mode: 'Bulk Batch Partition Transfer',
      execution_outcome: 'Completed Successfully',
      transferred_scope_summary: '8.4 GB in 8 partitions.',
      checkpoint_recovery_evidence_summary: 'Stage manifest committed and acknowledged by Snowflake stage API.'
    }
  },
  'CERT-VAL-2026-004': {
    id: 'CERT-VAL-2026-004',
    domain: 'VALIDATION',
    title: 'Customer Profile Referential Validation Certification',
    subject_name: 'Customer CRM Database',
    subject_id: 'val-crm-01',
    issued_at: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
    producer_authority: 'ValidationAssuranceEngine',
    decision: 'NOT_CERTIFIED',
    lifecycle: 'ACTIVE',
    summary: 'Validation evaluation identified 24 unmapped orphaned foreign keys in customer billing reference table.',
    scope_summary: '18 CRM tables evaluated across MySQL to Aurora PostgreSQL.',
    criteria: [
      {
        id: 'crit-val-04-01',
        name: 'Foreign Key Referential Parity',
        required_condition: 'Zero unresolved orphaned records in child tables.',
        observed_result: '24 orphaned rows detected in table `billing_subscriptions`.',
        outcome: 'NOT_SATISFIED',
        evidence_ref: 'EV-2026-VAL-04'
      }
    ],
    evidence: [
      {
        id: 'EV-2026-VAL-04',
        title: 'CRM Validation Discrepancy Manifest',
        artifact_type: 'DISCREPANCY_MANIFEST',
        subject_name: 'Customer CRM Database',
        sha256_digest: '7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 245).toISOString(),
        deep_link_route: '/reports/evidence'
      }
    ],
    exceptions: [
      {
        id: 'CERT-VAL-2026-004',
        condition: 'Foreign Key Drift in Billing Subscriptions Table',
        detail: '24 orphaned rows in billing_subscriptions table require operator repair before formal certification can be granted.',
        status: 'UNRESOLVED',
        updated_at: new Date(Date.now() - 1000 * 60 * 240).toISOString()
      }
    ],
    integrity: {
      sha256_fingerprint: '7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b',
      producer_authority: 'AKAAL Validation Engine v3.1',
      verification_status: 'VERIFIED',
      verification_method: 'SHA-256 Digest Match'
    },
    related_report_ids: ['REP-2026-0106'],
    validation_payload: {
      validation_scope_summary: '18 tables, 4,100,000 records evaluated.',
      source_target_comparison_summary: 'Source: MySQL Enterprise 8.0 | Target: Amazon Aurora PostgreSQL.',
      count_reconciliation_summary: 'Row count matches, but referential integrity violations exist.',
      checksum_merkle_summary: 'Discrepancies identified in table `billing_subscriptions`.',
      discrepancies_summary: '24 orphaned foreign keys detected.'
    }
  },
  'CERT-MIG-2026-005': {
    id: 'CERT-MIG-2026-005',
    domain: 'MIGRATION',
    title: 'Payment Stream CDC Replay Certification',
    subject_name: 'Global Order Stream Pipeline',
    subject_id: 'mig-stream-01',
    issued_at: new Date(Date.now() - 1000 * 60 * 320).toISOString(),
    producer_authority: 'MigrationAssuranceEngine',
    decision: 'PENDING_EVALUATION',
    lifecycle: 'ACTIVE',
    summary: 'Continuous CDC stream replication operating; formal evaluation pending 10 consecutive SLA windows under 500ms lag.',
    scope_summary: 'Live Kafka event stream topic `orders.payments.v1` replicating to ClickHouse.',
    criteria: [
      {
        id: 'crit-mig-05-01',
        name: 'Stream Lag Convergence Threshold',
        required_condition: 'Replication lag <= 500ms across 10 consecutive 5-minute sampling windows.',
        observed_result: 'Lag peaked at 3,420ms during burst traffic; currently at 640ms.',
        outcome: 'NOT_SATISFIED',
        evidence_ref: 'EV-2026-CDC-05'
      }
    ],
    evidence: [
      {
        id: 'EV-2026-CDC-05',
        title: 'Stream Lag Telemetry Manifest',
        artifact_type: 'TELEMETRY_MANIFEST',
        subject_name: 'Global Order Stream Pipeline',
        sha256_digest: '2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 325).toISOString(),
        deep_link_route: '/reports/evidence'
      }
    ],
    exceptions: [
      {
        id: 'CERT-MIG-2026-005',
        condition: 'CDC Stream Lag Precludes Formal Migration Certification',
        detail: 'Replication lag peaked at 3,420ms on target Aurora pool. Requires 10 consecutive evaluation windows within 500ms.',
        status: 'UNRESOLVED',
        updated_at: new Date(Date.now() - 1000 * 60 * 320).toISOString()
      }
    ],
    integrity: {
      sha256_fingerprint: '2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d',
      producer_authority: 'AKAAL CDC Engine v2.0',
      verification_status: 'VERIFIED',
      verification_method: 'SHA-256 Digest Match'
    },
    related_report_ids: ['REP-2026-0103', 'REP-2026-0105'],
    migration_payload: {
      execution_mode: 'Continuous CDC Stream Replay',
      execution_outcome: 'In Progress (SLA convergence evaluation ongoing)',
      transferred_scope_summary: '42.1K tx/sec continuous event stream.',
      checkpoint_recovery_evidence_summary: 'Kafka offset position committed every 100ms.'
    }
  },
  'CERT-VAL-2026-006': {
    id: 'CERT-VAL-2026-006',
    domain: 'VALIDATION',
    title: 'Historical Archive Ledger Verification Certification',
    subject_name: 'Enterprise Cold Storage Archive',
    subject_id: 'val-cold-01',
    issued_at: new Date(Date.now() - 1000 * 60 * 400).toISOString(),
    producer_authority: 'ValidationAssuranceEngine',
    decision: 'CERTIFIED',
    lifecycle: 'ACTIVE',
    summary: 'Immutable deep validation scan confirming zero bit rot or schema drift across 5-year cold storage archive.',
    scope_summary: '48 partitioned archive tables (120M records).',
    criteria: [
      {
        id: 'crit-val-06-01',
        name: 'Bit-Level Checksum Preservation',
        required_condition: 'All cold storage blocks match historical baseline checksums.',
        observed_result: '100% of 120M records verified against baseline hash chain.',
        outcome: 'SATISFIED',
        evidence_ref: 'EV-2026-VAL-06'
      }
    ],
    evidence: [
      {
        id: 'EV-2026-VAL-06',
        title: 'Cold Storage Merkle Audit Manifest',
        artifact_type: 'MERKLE_TREE_DIGEST',
        subject_name: 'Enterprise Cold Storage Archive',
        sha256_digest: '5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a',
        integrity_state: 'VERIFIED',
        created_at: new Date(Date.now() - 1000 * 60 * 410).toISOString(),
        deep_link_route: '/reports/evidence'
      }
    ],
    exceptions: [],
    integrity: {
      sha256_fingerprint: '5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a',
      producer_authority: 'AKAAL Validation Engine v3.1',
      verification_status: 'VERIFIED',
      verification_method: 'SHA-256 Digest Match'
    },
    related_report_ids: ['REP-2026-0108'],
    validation_payload: {
      validation_scope_summary: '48 partitioned archive tables, 120,000,000 rows.',
      source_target_comparison_summary: 'Source: Oracle 11g Archive | Target: ClickHouse Columnar Storage.',
      count_reconciliation_summary: '100% count equality verified.',
      checksum_merkle_summary: 'Zero bit rot discrepancies identified.',
      discrepancies_summary: 'Zero discrepancies.'
    }
  }
};

// Master canonical inventory fixtures (for all 14 report categories)
const INITIAL_LIBRARY_REPORTS: ReportItemDTO[] = [
  {
    id: 'REP-2026-0101',
    title: 'Dual-Engine Reconciliation & Verification Report',
    category: 'VALIDATION_RECONCILIATION',
    category_label: 'Validation & Reconciliation',
    subject_id: 'mig-core-banking-01',
    subject_name: 'Core Banking Ledger Migration',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    outcome: 'SATISFIED',
    summary: 'Dual-engine row hash comparison verified across 14,200,000 records with zero discrepancies.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-sha256-m8-core-01.json',
    download_formats: ['PDF', 'JSON', 'ZIP', 'CSV'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0102',
    title: 'Schema Translation & DDL Conformance Audit',
    category: 'SCHEMA_COMPATIBILITY',
    category_label: 'Schema & Compatibility',
    subject_id: 'mig-core-banking-01',
    subject_name: 'Core Banking Modernization',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 65).toISOString(),
    outcome: 'SATISFIED',
    summary: '142 tables, 318 indexes, and 48 sequences mapped with full semantic datatype parity.',
    certification_status: 'PENDING_EVALUATION',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-schema-ddl-conformance.json',
    download_formats: ['PDF', 'JSON'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0103',
    title: 'Continuous CDC LogMiner Replay Drift Analysis',
    category: 'CDC',
    category_label: 'CDC',
    subject_id: 'mig-core-banking-01',
    subject_name: 'Core Banking Ledger Migration',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 110).toISOString(),
    outcome: 'DEFECTS_FOUND',
    summary: 'Stream replication lag reached 3.4s during peak bulk replay; target pool saturated.',
    certification_status: 'UNDER_REVIEW',
    evidence_state: 'PARTIAL',
    evidence_manifest_ref: 'manifest-cdc-stream-offsets.json',
    download_formats: ['PDF', 'JSON', 'CSV'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0104',
    title: 'Snowflake Lakehouse Batch Partition Snapshot Verification',
    category: 'MIGRATION',
    category_label: 'Migration',
    subject_id: 'mig-ent-analytics',
    subject_name: 'Enterprise Data Lakehouse',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    outcome: 'CONVERGED',
    summary: 'Chunk transfer verified for partition 6/8 across 8.4 GB payload; 100% micro-batch match.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-snowflake-batch-p6.json',
    download_formats: ['PDF', 'JSON', 'CSV'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0105',
    title: 'Kafka Egress Throughput & Stage Latency Profile',
    category: 'PERFORMANCE',
    category_label: 'Performance',
    subject_id: 'mig-order-stream',
    subject_name: 'Global Commerce Modernization',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
    outcome: 'SATISFIED',
    summary: 'P95 sink batch apply latency stabilized at 18.4ms following broker rebalancing.',
    certification_status: 'NOT_ESTABLISHED',
    evidence_state: 'AVAILABLE',
    evidence_manifest_ref: 'manifest-kafka-perf-telemetry.json',
    download_formats: ['PDF', 'JSON', 'CSV'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0106',
    title: 'Delta Sync Watermark Ingestion & Referential Integrity',
    category: 'DATA_QUALITY',
    category_label: 'Data Quality',
    subject_id: 'mig-cust-profile',
    subject_name: 'Omnichannel Customer 360',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 360).toISOString(),
    outcome: 'RECONCILED',
    summary: 'Watermark offset polling confirmed 100% row consistency across 2,400,000 records.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-cust-referential-check.json',
    download_formats: ['PDF', 'JSON'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0107',
    title: 'Production Cutover Rehearsal & Readiness Assessment',
    category: 'CUTOVER_FAILBACK',
    category_label: 'Cutover & Failback',
    subject_id: 'mig-core-banking-01',
    subject_name: 'Core Banking Ledger Migration',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 420).toISOString(),
    outcome: 'SATISFIED',
    summary: 'All 4 readiness prerequisites satisfied; reverse CDC pipeline verified.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-cutover-rehearsal-01.json',
    download_formats: ['PDF', 'JSON', 'ZIP'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0108',
    title: 'Worker Failover & State Savepoint Reconstruction Audit',
    category: 'RECOVERY_RELIABILITY',
    category_label: 'Recovery & Reliability',
    subject_id: 'mig-ent-analytics',
    subject_name: 'Enterprise Data Lakehouse',
    subject_type: 'PLATFORM',
    generated_at: new Date(Date.now() - 1000 * 60 * 480).toISOString(),
    outcome: 'CONVERGED',
    summary: 'Restart reconstruction verified from durable checkpoint savepoint with zero record loss.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-recovery-checkpoint-480.json',
    download_formats: ['PDF', 'JSON'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0109',
    title: 'Data-in-Transit mTLS & Secret Access Verification',
    category: 'SECURITY',
    category_label: 'Security',
    subject_id: 'sec-cluster-prod',
    subject_name: 'Production Ingress Cluster',
    subject_type: 'PLATFORM',
    generated_at: new Date(Date.now() - 1000 * 60 * 540).toISOString(),
    outcome: 'SATISFIED',
    summary: '100% TLS 1.3 transport verified across 18 worker endpoints; zero unauthorized accesses.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-security-tls-audit.json',
    download_formats: ['PDF', 'JSON'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0110',
    title: 'Technical Control Evaluation & Separation of Duties',
    category: 'COMPLIANCE',
    category_label: 'Compliance',
    subject_id: 'comp-global-ledger',
    subject_name: 'Global Financial Ledger',
    subject_type: 'PROJECT',
    generated_at: new Date(Date.now() - 1000 * 60 * 600).toISOString(),
    outcome: 'SATISFIED',
    summary: '12 technical controls evaluated; 100% separation of duties verified between operator and approver.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-compliance-controls.json',
    download_formats: ['PDF', 'JSON', 'ZIP'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0111',
    title: 'Stage 4 Production Gate Dual-Control Quorum Ledger',
    category: 'GOVERNANCE_APPROVAL',
    category_label: 'Governance & Approval',
    subject_id: 'mig-core-banking-01',
    subject_name: 'Core Banking Ledger Migration',
    subject_type: 'MIGRATION',
    generated_at: new Date(Date.now() - 1000 * 60 * 660).toISOString(),
    outcome: 'SATISFIED',
    summary: 'Quorum of 3 approver roles cleared with binding conditions recorded.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-governance-approvals.json',
    download_formats: ['PDF', 'JSON'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0112',
    title: 'Operator Mutation & Privileged Access Action Journal',
    category: 'AUDIT',
    category_label: 'Audit',
    subject_id: 'audit-workspace-q3',
    subject_name: 'Production Workspace Operations',
    subject_type: 'AUDIT',
    generated_at: new Date(Date.now() - 1000 * 60 * 720).toISOString(),
    summary: 'Chronological append-only record of 184 operator mutations across migration pipelines.',
    evidence_state: 'AVAILABLE',
    evidence_manifest_ref: 'manifest-audit-journal-q3.json',
    download_formats: ['PDF', 'JSON', 'CSV'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0113',
    title: 'Worker Node Capacity & Lease Placement Inventory',
    category: 'INFRASTRUCTURE_FLEET',
    category_label: 'Infrastructure & Fleet',
    subject_id: 'fleet-us-east-cluster',
    subject_name: 'US-East Production Fleet',
    subject_type: 'PLATFORM',
    generated_at: new Date(Date.now() - 1000 * 60 * 780).toISOString(),
    summary: 'Cluster capacity at 48% utilization across 8 worker nodes; zero lease fencing events.',
    evidence_state: 'AVAILABLE',
    evidence_manifest_ref: 'manifest-fleet-inventory.json',
    download_formats: ['PDF', 'JSON'],
    deep_link_route: '/reports/library'
  },
  {
    id: 'REP-2026-0114',
    title: 'Executive Program Rollup & Modernization Status',
    category: 'EXECUTIVE',
    category_label: 'Executive',
    subject_id: 'prog-core-modernization',
    subject_name: 'Enterprise Modernization Program',
    subject_type: 'PROJECT',
    generated_at: new Date(Date.now() - 1000 * 60 * 840).toISOString(),
    outcome: 'SATISFIED',
    summary: 'Overall program completion at 82%; 4 of 5 critical workload certifications in good standing.',
    certification_status: 'CERTIFIED',
    evidence_state: 'VERIFIED',
    evidence_manifest_ref: 'manifest-exec-program-q3.json',
    download_formats: ['PDF', 'JSON'],
    deep_link_route: '/reports/library'
  }
];

// Helper to build a comprehensive detail envelope for any given report
function buildReportEnvelope(report: ReportItemDTO): ReportDetailEnvelopeDTO {
  let payload: ReportPayloadUnion;

  switch (report.category) {
    case 'MIGRATION':
      payload = {
        kind: 'MIGRATION',
        execution_summary: {
          total_objects: 142,
          completed_objects: 142,
          failed_objects: 0,
          skipped_objects: 0,
          total_bytes: 8420000000,
          total_rows: 14200000,
          elapsed_seconds: 1420,
          average_throughput_rows_sec: 10000,
          checkpoint_lsn_or_scn: '0/16B2D40'
        },
        stages: [
          { stage_number: 1, stage_name: 'Schema Pre-Validation', status: 'COMPLETED', duration_seconds: 45, transferred_rows: 0, transferred_bytes: 102400 },
          { stage_number: 2, stage_name: 'Snapshot Table Export', status: 'COMPLETED', duration_seconds: 820, transferred_rows: 14200000, transferred_bytes: 8200000000 },
          { stage_number: 3, stage_name: 'Secondary Index Build', status: 'COMPLETED', duration_seconds: 380, transferred_rows: 0, transferred_bytes: 180000000 },
          { stage_number: 4, stage_name: 'Dual-Engine Verification', status: 'COMPLETED', duration_seconds: 175, transferred_rows: 14200000, transferred_bytes: 40000000 }
        ],
        table_transfers: [
          { table_name: 'accounts', schema_name: 'public', row_count: 5000000, bytes: 2400000000, duration_seconds: 280, status: 'COMPLETED' },
          { table_name: 'ledger_entries', schema_name: 'public', row_count: 8500000, bytes: 5600000000, duration_seconds: 510, status: 'COMPLETED' },
          { table_name: 'currency_rates', schema_name: 'public', row_count: 700000, bytes: 420000000, duration_seconds: 30, status: 'COMPLETED' }
        ],
        failures_and_retries: []
      };
      break;

    case 'SCHEMA_COMPATIBILITY':
      payload = {
        kind: 'SCHEMA_COMPATIBILITY',
        assessment_summary: {
          total_objects_scanned: 508,
          compatible_objects: 492,
          partially_compatible: 16,
          incompatible_objects: 0,
          unsupported_features_count: 0,
          source_dialect: 'Oracle 19c Enterprise',
          target_dialect: 'PostgreSQL 16 (Aurora)'
        },
        object_inventory: [
          { object_type: 'TABLE', source_count: 142, target_compatible_count: 142, requires_manual_mapping: 0 },
          { object_type: 'INDEX', source_count: 318, target_compatible_count: 312, requires_manual_mapping: 6 },
          { object_type: 'SEQUENCE', source_count: 48, target_compatible_count: 48, requires_manual_mapping: 0 }
        ],
        type_mappings: [
          { source_type: 'NUMBER(12,2)', target_type: 'NUMERIC(12,2)', precision_preserved: true, notes: 'Exact financial precision mapped' },
          { source_type: 'VARCHAR2(255 BYTE)', target_type: 'VARCHAR(255)', precision_preserved: true },
          { source_type: 'RAW(16)', target_type: 'UUID', precision_preserved: true, notes: 'Standard RFC4122 translation' },
          { source_type: 'CLOB', target_type: 'TEXT', precision_preserved: true }
        ],
        unsupported_findings: [],
        drift_findings: []
      };
      break;

    case 'VALIDATION_RECONCILIATION':
      payload = {
        kind: 'VALIDATION_RECONCILIATION',
        validation_scope: {
          scope_name: 'Full Core Banking Reconciliation',
          entities_validated: 3,
          total_source_rows: 14200000,
          total_target_rows: 14200000,
          mismatch_rows: 0,
          checksum_algorithm: 'SHA-256 Merkle Row Hash Tree'
        },
        count_reconciliation: [
          { entity_name: 'accounts', source_count: 5000000, target_count: 5000000, delta: 0, status: 'MATCHED' },
          { entity_name: 'ledger_entries', source_count: 8500000, target_count: 8500000, delta: 0, status: 'MATCHED' },
          { entity_name: 'currency_rates', source_count: 700000, target_count: 700000, delta: 0, status: 'MATCHED' }
        ],
        checksum_results: [
          { entity_name: 'accounts', source_checksum: 'a8f3b2...c104', target_checksum: 'a8f3b2...c104', matched: true },
          { entity_name: 'ledger_entries', source_checksum: 'e7190c...5f92', target_checksum: 'e7190c...5f92', matched: true },
          { entity_name: 'currency_rates', source_checksum: '3b09fa...118d', target_checksum: '3b09fa...118d', matched: true }
        ],
        discrepancies: [],
        repair_results: []
      };
      break;

    case 'DATA_QUALITY':
      payload = {
        kind: 'DATA_QUALITY',
        quality_summary: {
          rules_evaluated: 8,
          rules_passed: 8,
          rules_failed: 0,
          total_records_checked: 2400000,
          quarantined_records: 0
        },
        rule_evaluations: [
          { rule_id: 'DQ-01', rule_name: 'Customer ID Non-Null Guard', entity_name: 'customers', rule_type: 'NULL_CHECK', violation_count: 0, status: 'PASSED' },
          { rule_id: 'DQ-02', rule_name: 'Email Format Conformance', entity_name: 'customers', rule_type: 'FORMAT_VALIDATION', violation_count: 0, status: 'PASSED' },
          { rule_id: 'DQ-03', rule_name: 'Ledger Foreign Key Integrity', entity_name: 'ledger_entries', rule_type: 'REFERENTIAL_INTEGRITY', violation_count: 0, status: 'PASSED' }
        ],
        cleansing_outcomes: [
          { entity_name: 'customers', field_name: 'phone_number', transform_type: 'E.164 Standardization', records_transformed: 42000 }
        ],
        quarantine_records: []
      };
      break;

    case 'PERFORMANCE':
      payload = {
        kind: 'PERFORMANCE',
        summary: {
          total_duration_seconds: 1420,
          effective_throughput_rows_sec: 10000,
          effective_throughput_mb_sec: 5.92,
          total_volume_bytes: 8420000000,
          total_records: 14200000
        },
        stage_durations: [
          { stage_name: 'Snapshot Table Export', duration_seconds: 820, percentage_of_total: 58 },
          { stage_name: 'Secondary Index Build', duration_seconds: 380, percentage_of_total: 27 },
          { stage_name: 'Dual-Engine Verification', duration_seconds: 175, percentage_of_total: 12 },
          { stage_name: 'Pre-Validation & Setup', duration_seconds: 45, percentage_of_total: 3 }
        ],
        partition_throughput: [
          { partition_id: 'part-01', entity_name: 'ledger_entries', row_count: 4250000, duration_seconds: 240, rows_per_second: 17708 },
          { partition_id: 'part-02', entity_name: 'ledger_entries', row_count: 4250000, duration_seconds: 270, rows_per_second: 15740 }
        ],
        durable_notes: [
          'Throughput velocity calculated from durable stage start and completion timestamps.',
          'Partition parallel factor was 4 worker threads.'
        ],
        unavailable_telemetry_notice: 'High-resolution time-series metrics (P95/P99 latency curves, sub-second CPU/memory graphs) are ephemeral Monitoring telemetry and are not recorded in durable report archives.'
      };
      break;

    case 'CDC':
      payload = {
        kind: 'CDC',
        summary: {
          capture_status: 'STREAMING',
          apply_status: 'LAGGING',
          total_transactions_captured: 842000,
          total_transactions_applied: 839150,
          quarantined_events: 12
        },
        boundary_positions: [
          { stream_name: 'core_ledger_cdc', provider_type: 'ORACLE', position_label: 'SCN', current_position: '18492048', committed_position: '18489200', lag_records: 2850 }
        ],
        transaction_totals: [
          { operation: 'INSERT', count: 620000 },
          { operation: 'UPDATE', count: 210000 },
          { operation: 'DELETE', count: 12000 },
          { operation: 'DDL', count: 0 }
        ],
        conflicts_and_quarantine: [
          { event_id: 'EVT-CDC-081', table_name: 'ledger_entries', conflict_type: 'ROW_NOT_FOUND', position: 'SCN: 18491002', occurred_at: new Date(Date.now() - 1000 * 60 * 110).toISOString(), status: 'QUARANTINED' }
        ]
      };
      break;

    case 'CUTOVER_FAILBACK':
      payload = {
        kind: 'CUTOVER_FAILBACK',
        cutover_summary: {
          decision_state: 'APPROVED',
          final_catchup_lag_seconds: 0.18,
          readiness_score_or_status: 'All Prerequisites Verified',
          operator_in_charge: 'Aalok Ladwa (Lead Architect)'
        },
        readiness_evidence: [
          { check_item: 'CDC Replication Catch-up (<500ms)', category: 'CDC_DRAIN', status: 'SATISFIED', verified_at: new Date(Date.now() - 1000 * 60 * 420).toISOString() },
          { check_item: 'Dual-Engine Full Schema Verification', category: 'SCHEMA_VERIFICATION', status: 'SATISFIED', verified_at: new Date(Date.now() - 1000 * 60 * 422).toISOString() },
          { check_item: 'Target Write Permission & Role Guard', category: 'PERMISSION_GUARD', status: 'SATISFIED', verified_at: new Date(Date.now() - 1000 * 60 * 425).toISOString() }
        ],
        approval_gates: [
          { gate_name: 'Infrastructure & DB Lead Sign-off', approver_role: 'Database Administrator', decision: 'APPROVED', decided_at: new Date(Date.now() - 1000 * 60 * 430).toISOString(), decision_notes: 'Target pool sizing verified.' },
          { gate_name: 'Application Owner Sign-off', approver_role: 'Principal Engineer', decision: 'APPROVED', decided_at: new Date(Date.now() - 1000 * 60 * 432).toISOString() }
        ],
        transition_milestones: [
          { timestamp: new Date(Date.now() - 1000 * 60 * 420).toISOString(), milestone: 'Source Writes Paused & Buffer Drained', status: 'COMPLETED' },
          { timestamp: new Date(Date.now() - 1000 * 60 * 418).toISOString(), milestone: 'Final Sequence Re-alignment Applied', status: 'COMPLETED' },
          { timestamp: new Date(Date.now() - 1000 * 60 * 415).toISOString(), milestone: 'Target Aurora Connection Pool Unlocked', status: 'COMPLETED' }
        ],
        failback_readiness: {
          reverse_cdc_stream_configured: true,
          target_snapshot_available: true,
          failback_procedure_status: 'Reverse Replication Pipeline Ready'
        }
      };
      break;

    case 'RECOVERY_RELIABILITY':
      payload = {
        kind: 'RECOVERY_RELIABILITY',
        recovery_summary: {
          total_failures_encountered: 1,
          automatic_restarts: 1,
          manual_interventions: 0,
          last_known_checkpoint: 'savepoint-raft-cp-480'
        },
        failure_events: [
          { event_id: 'FL-01', component: 'worker-02.us-east', failure_type: 'Worker Node OOM Socket Reset', occurred_at: new Date(Date.now() - 1000 * 60 * 490).toISOString(), recovery_action: 'State reconstructed from RocksDB savepoint on worker-03', recovered_at: new Date(Date.now() - 1000 * 60 * 485).toISOString(), resolution_status: 'RESOLVED' }
        ],
        checkpoint_history: [
          { checkpoint_id: 'cp-480', timestamp: new Date(Date.now() - 1000 * 60 * 480).toISOString(), reconstructed_state_byte_size: 14200000, durable_reference: 'raft-log-offset-98421' }
        ],
        lease_and_fencing_evidence: [
          { worker_node_id: 'worker-02', lease_acquired_at: new Date(Date.now() - 1000 * 60 * 600).toISOString(), lease_fenced_at: new Date(Date.now() - 1000 * 60 * 490).toISOString(), fencing_reason: 'Heartbeat timeout; fencing token revoked' }
        ]
      };
      break;

    case 'SECURITY':
      payload = {
        kind: 'SECURITY',
        security_scope: {
          audit_scope_name: 'Production Ingress & Data-in-Transit Scope',
          total_access_evaluations: 14200,
          denied_operations_count: 0,
          active_identity_sessions: 4
        },
        authorization_activity: [
          { timestamp: new Date(Date.now() - 1000 * 60 * 540).toISOString(), principal: 'svc-migration-worker', action: 'READ_STREAM', resource: 'oracle.core_banking', decision: 'ALLOW', policy_name: 'pol-migration-rw' }
        ],
        denied_operations: [],
        identity_and_session_findings: [],
        transport_security_evidence: [
          { endpoint: 'aurora-cluster-target.internal:5432', tls_version: 'TLS 1.3', certificate_subject: 'CN=aurora.internal', valid_until: '2027-12-31' }
        ]
      };
      break;

    case 'COMPLIANCE':
      payload = {
        kind: 'COMPLIANCE',
        compliance_scope: {
          framework_mapping_name: 'Financial Data Handling & Auditability Controls',
          controls_evaluated: 12,
          controls_passed: 12,
          controls_with_exceptions: 0
        },
        technical_controls: [
          { control_id: 'CTRL-01', control_name: 'Dual-Control Cutover Authorization', domain: 'ACCESS_CONTROL', evaluation_result: 'SATISFIED', evidence_reference: 'manifest-cutover-rehearsal-01.json' },
          { control_id: 'CTRL-02', control_name: 'Cryptographic Row Digest Parity', domain: 'INTEGRITY_VERIFICATION', evaluation_result: 'SATISFIED', evidence_reference: 'manifest-sha256-m8-core-01.json' },
          { control_id: 'CTRL-03', control_name: 'PII Field Level Masking Verification', domain: 'DATA_PROTECTION', evaluation_result: 'SATISFIED', evidence_reference: 'manifest-compliance-controls.json' }
        ],
        separation_of_duties_records: [
          { activity_type: 'CUTOVER_EXECUTION', operator_a: 'Aalok Ladwa (Executer)', operator_b: 'Sarah Jenkins (Authorizer)', verified_independent: true }
        ],
        data_protection_evidence: [
          { table_or_column: 'customers.ssn_tax_id', masking_rule: 'SHA-256 HMAC Salt Hash', redaction_verified: true }
        ],
        exceptions: []
      };
      break;

    case 'GOVERNANCE_APPROVAL':
      payload = {
        kind: 'GOVERNANCE_APPROVAL',
        governance_summary: {
          plan_name: 'Production Migration Plan',
          plan_version: '2.4',
          barrier_status: 'CLEARED',
          required_quorum_count: 2,
          received_approvals_count: 2
        },
        approval_barriers: [
          { barrier_id: 'GATE-04-PROD', barrier_title: 'Stage 4 Production Execution Gate', stage_locked: 'Cutover & Switchover', status: 'CLEARED' }
        ],
        decision_records: [
          { record_id: 'DEC-01', barrier_id: 'GATE-04-PROD', approver_name: 'Aalok Ladwa', approver_role: 'Lead Architect', decision: 'APPROVED', decided_at: new Date(Date.now() - 1000 * 60 * 660).toISOString(), notes: 'Verification digests matched 100%.' },
          { record_id: 'DEC-02', barrier_id: 'GATE-04-PROD', approver_name: 'Elena Rostova', approver_role: 'Head of Operations', decision: 'APPROVED', decided_at: new Date(Date.now() - 1000 * 60 * 658).toISOString(), notes: 'Maintenance window confirmed.' }
        ],
        conditions_and_expiry: [
          { condition_id: 'COND-01', description: 'Execution must initiate within 4-hour maintenance window', satisfied: true, expires_at: new Date(Date.now() + 1000 * 60 * 240).toISOString() }
        ]
      };
      break;

    case 'AUDIT':
      payload = {
        kind: 'AUDIT',
        audit_scope: {
          time_window_start: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
          time_window_end: new Date().toISOString(),
          total_events_recorded: 184,
          privileged_actions_count: 4,
          failed_operations_count: 0
        },
        records: [
          { timestamp: new Date(Date.now() - 1000 * 60 * 720).toISOString(), actor: 'aalok.ladwa', action: 'INITIATE_CUTOVER_REHEARSAL', target: 'mig-core-banking-01', result: 'SUCCESS', context: 'Workspace: Core Banking' },
          { timestamp: new Date(Date.now() - 1000 * 60 * 715).toISOString(), actor: 'system.engine', action: 'EXECUTE_VERIFICATION_PROBE', target: 'db-aurora-target', result: 'SUCCESS', context: 'Validation: M8 Full' },
          { timestamp: new Date(Date.now() - 1000 * 60 * 710).toISOString(), actor: 'elena.rostova', action: 'CLEAR_APPROVAL_BARRIER', target: 'GATE-04-PROD', result: 'SUCCESS', context: 'Plan: v2.4' }
        ],
        privileged_actions: [
          { timestamp: new Date(Date.now() - 1000 * 60 * 720).toISOString(), actor: 'aalok.ladwa', elevated_action: 'OVERRIDE_MAINTENANCE_LOCK', justification: 'Rehearsal test window authorized by ticket OPS-9142' }
        ]
      };
      break;

    case 'INFRASTRUCTURE_FLEET':
      payload = {
        kind: 'INFRASTRUCTURE_FLEET',
        fleet_summary: {
          total_nodes: 8,
          active_workers: 8,
          draining_nodes: 0,
          cluster_capacity_utilization_pct: 48
        },
        node_inventory: [
          { node_id: 'node-01.us-east.prod', role: 'COORDINATOR', assigned_workloads: 4, cpu_utilization_pct: 38, memory_utilization_pct: 44, status: 'HEALTHY' },
          { node_id: 'node-02.us-east.prod', role: 'WORKER', assigned_workloads: 6, cpu_utilization_pct: 54, memory_utilization_pct: 62, status: 'HEALTHY' },
          { node_id: 'node-03.us-east.prod', role: 'WORKER', assigned_workloads: 5, cpu_utilization_pct: 48, memory_utilization_pct: 50, status: 'HEALTHY' }
        ],
        workload_placement: [
          { workload_id: 'mig-core-banking-01', workload_name: 'Core Banking Ledger Migration', assigned_node: 'node-02.us-east.prod', lease_status: 'ACTIVE' },
          { workload_id: 'mig-ent-analytics', workload_name: 'Enterprise Data Lakehouse', assigned_node: 'node-03.us-east.prod', lease_status: 'ACTIVE' }
        ],
        historical_fleet_logs: [
          { timestamp: new Date(Date.now() - 1000 * 60 * 780).toISOString(), event_type: 'WORKLOAD_REBALANCED', details: 'Core Banking pipeline assigned to worker node-02' }
        ]
      };
      break;

    case 'EXECUTIVE':
    default:
      payload = {
        kind: 'EXECUTIVE',
        executive_summary: {
          program_name: 'Enterprise Cloud Modernization Initiative',
          overall_completion_pct: 82,
          readiness_status: 'ON_TRACK',
          total_workloads: 6,
          certified_workloads: 5
        },
        program_milestones: [
          { milestone_name: 'Phase 1: Customer Profile & Analytics Migration', target_date: '2026-08-30', status: 'COMPLETED', verified_reference_report_id: 'REP-2026-0104' },
          { milestone_name: 'Phase 2: Core Banking Ledger Migration & Verification', target_date: '2026-09-15', status: 'IN_PROGRESS', verified_reference_report_id: 'REP-2026-0101' },
          { milestone_name: 'Phase 3: Production Switchover & Cutover', target_date: '2026-09-30', status: 'PENDING', verified_reference_report_id: 'REP-2026-0107' }
        ],
        technical_domain_summaries: [
          { domain: 'Validation & Cryptographic Reconciliation', status: 'SATISFIED', findings_count: 0, linked_report_id: 'REP-2026-0101' },
          { domain: 'Schema & Datatype Parity', status: 'SATISFIED', findings_count: 0, linked_report_id: 'REP-2026-0102' },
          { domain: 'Continuous CDC Replication Lag', status: 'ATTENTION', findings_count: 1, linked_report_id: 'REP-2026-0103' },
          { domain: 'Production Cutover Readiness', status: 'SATISFIED', findings_count: 0, linked_report_id: 'REP-2026-0107' }
        ],
        risks_and_exceptions: [
          { risk_id: 'RISK-01', headline: 'CDC Replication Lag during Peak Replay', severity: 'HIGH', mitigation_action: 'Allocated 4 additional Aurora sink connections to target pool.', linked_report_id: 'REP-2026-0103' }
        ]
      };
      break;
  }

  return {
    id: report.id,
    title: report.title,
    category: report.category,
    category_label: report.category_label,
    subject_id: report.subject_id,
    subject_name: report.subject_name,
    subject_type: report.subject_type,
    generated_at: report.generated_at,
    outcome: report.outcome,
    summary: report.summary,
    available_export_formats: report.download_formats,
    scope_and_inputs: {
      tenant: 'Enterprise Tenant (prod-us-east-1)',
      workspace: 'Core Financial Services',
      project_name: 'Enterprise Cloud Migration 2026',
      migration_name: report.subject_name,
      run_id: 'run-' + report.id.toLowerCase(),
      plan_version: 'v2.4.1',
      execution_mode: 'High-Concurrency Dual-Engine',
      source_instance: 'Oracle 19c Enterprise (db-oracle-source.internal)',
      target_instance: 'PostgreSQL 16 Aurora (db-aurora-target.internal)',
      time_window_start: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
      time_window_end: report.generated_at
    },
    trust_and_provenance: {
      report_id: report.id,
      generated_at: report.generated_at,
      producer_engine: 'AKAAL Unified Reporting & Assurance Subsystem',
      producer_version: 'v2.0.0-release (M8 Engine)',
      run_or_plan_binding: 'plan-v2.4.1 :: run-' + report.id.toLowerCase(),
      artifact_sha256_fingerprint: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      integrity_state: 'VERIFIED',
      completeness: 'COMPLETE',
      evidence_references: report.evidence_manifest_ref ? [report.evidence_manifest_ref] : []
    },
    related_evidence: [
      {
        id: 'EV-' + report.id,
        title: report.title + ' — Cryptographic Manifest',
        artifact_type: 'SHA-256 Digest Manifest',
        subject_name: report.subject_name,
        sha256_digest: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        integrity_state: 'VERIFIED',
        created_at: report.generated_at,
        byte_size: 42800,
        deep_link_route: '/reports/evidence'
      }
    ],
    payload
  };
}

@Injectable({
  providedIn: 'root'
})
export class ReportsService {
  constructor(private ipc?: IpcService) {}

  // Section Loading States
  public summaryState = signal<SectionLoadingState>('AVAILABLE_WITH_DATA');
  public reportsState = signal<SectionLoadingState>('AVAILABLE_WITH_DATA');
  public certificationState = signal<SectionLoadingState>('AVAILABLE_WITH_DATA');
  public evidenceState = signal<SectionLoadingState>('AVAILABLE_WITH_DATA');
  public libraryState = signal<SectionLoadingState>('AVAILABLE_WITH_DATA');

  // Master Data Signals
  private _summary = signal<ReportsSummaryMetricsDTO>({
    total_reports_count: INITIAL_LIBRARY_REPORTS.length,
    certification_attention_count: 2,
    evidence_manifests_count: 5,
    observed_at: new Date().toISOString()
  });
  private _allReports = signal<ReportItemDTO[]>(INITIAL_LIBRARY_REPORTS);
  private _certificationAttention = signal<CertificationAttentionItemDTO[]>([
    {
      id: 'ATT-CERT-01',
      subject_name: 'Core Banking Ledger Migration',
      subject_type: 'MIGRATION',
      condition_type: 'UNRESOLVED_DISCREPANCY',
      severity: 'HIGH',
      headline: 'CDC Stream Lag Prevents Formal Migration Certification',
      detail: 'Replication lag spiked to 3,420ms on target Aurora pool. Requires 10 consecutive evaluation windows within 500ms.',
      related_report_id: 'REP-2026-0103',
      related_report_title: 'Continuous CDC LogMiner Replay Drift Analysis',
      detected_at: new Date(Date.now() - 1000 * 60 * 110).toISOString(),
      deep_link: '/reports/certification'
    },
    {
      id: 'ATT-CERT-02',
      subject_name: 'Global Order Stream Pipeline',
      subject_type: 'MIGRATION',
      condition_type: 'CRITERIA_GAP',
      severity: 'MEDIUM',
      headline: 'Formal Trust & Certification Criteria Not Yet Established',
      detail: 'Workload operating in continuous replication without a formal compliance or validation attestation profile attached.',
      related_report_id: 'REP-2026-0105',
      related_report_title: 'Kafka Egress Throughput & Stage Latency Profile',
      detected_at: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
      deep_link: '/reports/certification'
    }
  ]);
  private _evidenceActivity = signal<EvidenceActivityItemDTO[]>([
    {
      id: 'EV-ACT-01',
      activity_type: 'MANIFEST_GENERATED',
      subject_name: 'Core Banking Ledger M8 Run',
      occurred_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
      artifact_type: 'SHA-256 Digest Manifest',
      verification_status: 'VERIFIED',
      summary: 'Generated canonical manifest containing 14.2M row checksums with zero digest mismatch.',
      deep_link: '/reports/evidence'
    },
    {
      id: 'EV-ACT-02',
      activity_type: 'INTEGRITY_VERIFIED',
      subject_name: 'Production Cutover Approval Pack',
      occurred_at: new Date(Date.now() - 1000 * 60 * 420).toISOString(),
      artifact_type: 'Audit Evidence Package',
      verification_status: 'VERIFIED',
      summary: 'Package verified with operator and compliance lead tokens under Four-Eyes Principle.',
      deep_link: '/reports/evidence'
    },
    {
      id: 'EV-ACT-03',
      activity_type: 'DIGEST_VERIFIED',
      subject_name: 'RocksDB Raft Checkpoint Snapshot',
      occurred_at: new Date(Date.now() - 1000 * 60 * 480).toISOString(),
      artifact_type: 'Durability Savepoint Manifest',
      verification_status: 'VERIFIED',
      summary: 'Cluster consensus verified on worker-02; checkpoint storage intact.',
      deep_link: '/reports/evidence'
    }
  ]);

  // Library Navigation & Active Report State
  public activeLibraryView = signal<LibraryViewMode>('CATALOG');
  public selectedCategory = signal<ReportCategoryKey | null>(null);
  public selectedReport = signal<ReportDetailEnvelopeDTO | null>(null);

  // Library Inventory Filters & Pagination
  public inventorySearchQuery = signal<string>('');
  public inventoryCategoryFilter = signal<string>('ALL');
  public inventoryOutcomeFilter = signal<string>('ALL');
  public inventorySortField = signal<'generated_at' | 'title' | 'category'>('generated_at');
  public inventorySortDirection = signal<'asc' | 'desc'>('desc');
  public inventoryPageIndex = signal<number>(1);
  public inventoryPageSize = signal<number>(8);

  // Export Modal State
  public isExportModalOpen = signal<boolean>(false);
  public exportTargetReport = signal<ReportItemDTO | ReportDetailEnvelopeDTO | null>(null);
  public isExporting = signal<boolean>(false);
  public lastExportResult = signal<ExportResponseDTO | null>(null);

  // Home Page Search Signal
  public reportSearchQuery = signal<string>('');

  // Status Signal
  public isRefreshing = signal<boolean>(false);

  // Text Formatter Helper Reference
  public formatText = formatReportText;

  // Categories definition
  public categories = REPORT_CATEGORIES;

  // Computed Projections (Home Bounded Preview)
  public summary = computed(() => this._summary());
  public recentReports = computed(() => this._allReports().slice(0, 8));
  public certificationAttention = computed(() => this._certificationAttention().slice(0, 6));
  public evidenceActivity = computed(() => this._evidenceActivity().slice(0, 6));

  public hasCertificationAttention = computed(() => this._certificationAttention().length > 0);
  public hasEvidenceActivity = computed(() => this._evidenceActivity().length > 0);

  // Filtered Home Recent Reports
  public filteredReports = computed<ReportItemDTO[]>(() => {
    const q = this.reportSearchQuery().toLowerCase().trim();
    const list = this._allReports();

    if (!q) return list.slice(0, 8);

    return list.filter(report => 
      report.title.toLowerCase().includes(q) ||
      report.id.toLowerCase().includes(q) ||
      report.subject_name.toLowerCase().includes(q) ||
      report.category_label.toLowerCase().includes(q)
    ).slice(0, 8);
  });

  // Filtered Library Inventory
  public filteredInventoryReports = computed<ReportItemDTO[]>(() => {
    const q = this.inventorySearchQuery().toLowerCase().trim();
    const cat = this.inventoryCategoryFilter();
    const outcome = this.inventoryOutcomeFilter();
    let list = this._allReports();

    if (cat !== 'ALL') {
      list = list.filter(r => r.category === cat);
    }

    if (outcome !== 'ALL') {
      list = list.filter(r => r.outcome === outcome);
    }

    if (q) {
      list = list.filter(r => 
        r.title.toLowerCase().includes(q) ||
        r.id.toLowerCase().includes(q) ||
        r.subject_name.toLowerCase().includes(q) ||
        r.category_label.toLowerCase().includes(q)
      );
    }

    // Sort
    const field = this.inventorySortField();
    const dir = this.inventorySortDirection();
    return [...list].sort((a, b) => {
      let valA: string = a[field] || '';
      let valB: string = b[field] || '';
      if (field === 'generated_at') {
        const timeA = new Date(valA).getTime();
        const timeB = new Date(valB).getTime();
        return dir === 'desc' ? timeB - timeA : timeA - timeB;
      }
      const cmp = valA.localeCompare(valB);
      return dir === 'desc' ? -cmp : cmp;
    });
  });

  // Paginated Library Inventory
  public paginatedInventoryReports = computed<ReportItemDTO[]>(() => {
    const list = this.filteredInventoryReports();
    const page = this.inventoryPageIndex();
    const size = this.inventoryPageSize();
    const start = (page - 1) * size;
    return list.slice(start, start + size);
  });

  public totalInventoryPages = computed<number>(() => {
    const count = this.filteredInventoryReports().length;
    const size = this.inventoryPageSize();
    return Math.max(1, Math.ceil(count / size));
  });

  // Category-Scoped Reports
  public categoryScopedReports = computed<ReportItemDTO[]>(() => {
    const selected = this.selectedCategory();
    if (!selected) return [];
    return this._allReports().filter(r => r.category === selected);
  });

  public getCategoryDefinition(key: ReportCategoryKey | string | null) {
    if (!key) return null;
    return this.categories.find(c => c.key === key) || null;
  }

  // Navigation Methods
  public selectLibraryView(view: LibraryViewMode): void {
    this.activeLibraryView.set(view);
    if (view === 'INVENTORY') {
      this.inventoryCategoryFilter.set('ALL');
    }
  }

  public selectCategory(categoryKey: ReportCategoryKey): void {
    this.selectedCategory.set(categoryKey);
    this.activeLibraryView.set('CATEGORY_VIEW');
  }

  public openReportById(reportId: string): void {
    const found = this._allReports().find(r => r.id === reportId);
    if (found) {
      const envelope = buildReportEnvelope(found);
      this.selectedReport.set(envelope);
      this.activeLibraryView.set('REPORT_DETAIL');
    } else {
      // Default to first report if not found or sample
      const fallback = this._allReports()[0];
      if (fallback) {
        this.selectedReport.set(buildReportEnvelope(fallback));
        this.activeLibraryView.set('REPORT_DETAIL');
      }
    }
  }

  public closeReport(): void {
    this.selectedReport.set(null);
    if (this.selectedCategory()) {
      this.activeLibraryView.set('CATEGORY_VIEW');
    } else {
      this.activeLibraryView.set('CATALOG');
    }
  }

  public openExportModal(report: ReportItemDTO | ReportDetailEnvelopeDTO): void {
    this.exportTargetReport.set(report);
    this.lastExportResult.set(null);
    this.isExportModalOpen.set(true);
  }

  public closeExportModal(): void {
    this.isExportModalOpen.set(false);
    this.exportTargetReport.set(null);
    this.isExporting.set(false);
  }

  public dispatchExport(format: ExportFormat): void {
    const target = this.exportTargetReport();
    if (!target) return;

    this.isExporting.set(true);

    setTimeout(() => {
      this.isExporting.set(false);
      const ext = format.toLowerCase();
      const filename = `${target.id.toLowerCase()}_${target.category.toLowerCase()}_export.${ext}`;
      this.lastExportResult.set({
        export_id: 'EXP-' + Math.random().toString(36).substring(2, 9).toUpperCase(),
        report_id: target.id,
        format,
        status: 'READY',
        file_name: filename,
        byte_size: format === 'ZIP' ? 428000 : (format === 'PDF' ? 184000 : 12400),
        generated_at: new Date().toISOString()
      });
    }, 600);
  }

  public refresh(): void {
    this.isRefreshing.set(true);
    setTimeout(() => {
      this.isRefreshing.set(false);
    }, 400);
  }

  public initializeState(customData?: Partial<ReportsHomeDataDTO>): void {
    if (customData) {
      if (customData.summary) this._summary.set(customData.summary);
      if (customData.recent_reports) this._allReports.set(customData.recent_reports);
      if (customData.certification_attention) this._certificationAttention.set(customData.certification_attention);
      if (customData.evidence_activity) this._evidenceActivity.set(customData.evidence_activity);
    }
  }

  public setSectionState(
    section: 'summary' | 'reports' | 'certification' | 'evidence' | 'library', 
    state: SectionLoadingState
  ): void {
    switch (section) {
      case 'summary':
        this.summaryState.set(state);
        break;
      case 'reports':
        this.reportsState.set(state);
        break;
      case 'certification':
        this.certificationState.set(state);
        break;
      case 'evidence':
        this.evidenceState.set(state);
        break;
      case 'library':
        this.libraryState.set(state);
        break;
    }
  }

  // =========================================================================
  // PART 3: TRUST & CERTIFICATION STATE
  // =========================================================================

  public activeCertTab = signal<CertificationViewMode>('OVERVIEW');
  public selectedCertId = signal<string | null>(null);

  private _certEnvelopes = signal<Record<string, CertificationDetailEnvelopeDTO>>(INITIAL_CERTIFICATION_ENVELOPES);
  
  public allCertifications = computed<CertificationSummaryDTO[]>(() => {
    return Object.values(this._certEnvelopes()).map(env => ({
      id: env.id,
      domain: env.domain,
      title: env.title,
      subject_name: env.subject_name,
      subject_id: env.subject_id,
      issued_at: env.issued_at,
      decision: env.decision,
      lifecycle: env.lifecycle,
      summary: env.summary
    }));
  });

  public selectedCertification = computed<CertificationDetailEnvelopeDTO | null>(() => {
    const id = this.selectedCertId();
    if (!id) return null;
    return this._certEnvelopes()[id] || null;
  });

  public recentCertifications = computed(() => this.allCertifications());

  public certAttentionItems = signal<CertificationExceptionDTO[]>([
    {
      id: 'CERT-VAL-2026-004',
      condition: 'Foreign Key Drift in Billing Subscriptions Table',
      detail: '24 orphaned rows in billing_subscriptions table require operator repair before formal certification can be granted.',
      status: 'UNRESOLVED',
      updated_at: new Date(Date.now() - 1000 * 60 * 240).toISOString()
    },
    {
      id: 'CERT-MIG-2026-005',
      condition: 'CDC Stream Lag Precludes Formal Migration Certification',
      detail: 'Replication lag peaked at 3,420ms on target Aurora pool. Requires 10 consecutive evaluation windows within 500ms.',
      status: 'UNRESOLVED',
      updated_at: new Date(Date.now() - 1000 * 60 * 320).toISOString()
    }
  ]);

  public activeVerificationResult = signal<VerificationResultDTO | null>(null);

  public selectCertificationTab(tab: CertificationViewMode): void {
    this.activeCertTab.set(tab);
    this.selectedCertId.set(null);
  }

  public openCertificationById(certId: string): void {
    this.selectedCertId.set(certId);
  }

  public clearSelectedCertification(): void {
    this.selectedCertId.set(null);
  }

  public verificationHistory = signal<VerificationResultDTO[]>([
    {
      target_identifier: 'CERT-MIG-2026-001',
      target_type: 'CERTIFICATION',
      method: 'SHA-256 Digest Match',
      result_status: 'VERIFIED',
      verified_at: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
      stored_fingerprint: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
      computed_fingerprint: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
      detail_notes: 'Stored SHA-256 digest matches computed hash for the migration certification envelope.'
    },
    {
      target_identifier: 'CERT-VAL-2026-002',
      target_type: 'CERTIFICATION',
      method: 'SHA-256 Digest Match',
      result_status: 'VERIFIED',
      verified_at: new Date(Date.now() - 1000 * 60 * 58).toISOString(),
      stored_fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      computed_fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      detail_notes: 'Validation Merkle root hash matches expected state with zero bit divergence.'
    },
    {
      target_identifier: 'EV-2026-VAL-01',
      target_type: 'EVIDENCE_ARTIFACT',
      method: 'SHA-256 Digest Match',
      result_status: 'VERIFIED',
      verified_at: new Date(Date.now() - 1000 * 60 * 65).toISOString(),
      stored_fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      computed_fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      detail_notes: 'Evidence manifest digest matches attached proof artifact.'
    }
  ]);

  public recentVerifications = computed(() => this.verificationHistory());

  // --------------------------------------------------------------------------
  // PART 4: EVIDENCE PORTAL SIGNALS & SELECTORS
  // --------------------------------------------------------------------------
  public activeEvidenceTab = signal<EvidenceTabMode>('EXPLORER');
  public evidenceFilters = signal<EvidencePaginationQuery>({
    search_query: '',
    artifact_type: 'ALL',
    lifecycle: 'ALL',
    sort_field: 'created_at',
    sort_direction: 'desc',
    page_index: 0,
    page_size: 10
  });

  public selectedEvidenceId = signal<string | null>(null);
  public selectedDossierId = signal<string | null>(null);
  public selectedCertArtifactId = signal<string | null>(null);
  public selectedPackageId = signal<string | null>(null);

  public evidenceItems = signal<EvidenceItemDTO[]>([
    {
      id: 'EV-2026-MIG-01',
      title: 'Partition Bulk Transfer Manifest',
      artifact_type: 'MANIFEST_SNAPSHOT',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 50).toISOString(),
      producer_authority: 'MigrationAssuranceEngine',
      fingerprint: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
      byte_size: 4194304,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      dossier_id: 'DOS-2026-001',
      certificate_id: 'CERT-MIG-2026-001',
      report_id: 'REP-2026-0101',
      deep_link_route: '/reports/evidence'
    },
    {
      id: 'EV-2026-VAL-01',
      title: 'Dual-Engine Validation Merkle Root Digest',
      artifact_type: 'MERKLE_TREE_DIGEST',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 48).toISOString(),
      producer_authority: 'ValidationAssuranceEngine',
      fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      byte_size: 1048576,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      dossier_id: 'DOS-2026-001',
      certificate_id: 'CERT-VAL-2026-002',
      report_id: 'REP-2026-0101',
      deep_link_route: '/reports/evidence'
    },
    {
      id: 'EV-2026-GOV-01',
      title: 'Dual-Control Sign-off Ledger Record',
      artifact_type: 'GOVERNANCE_LEDGER',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 46).toISOString(),
      producer_authority: 'GovernanceSecurityBarrier',
      fingerprint: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
      byte_size: 262144,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      dossier_id: 'DOS-2026-001',
      certificate_id: 'CERT-MIG-2026-001',
      report_id: 'REP-2026-0101',
      deep_link_route: '/reports/evidence'
    },
    {
      id: 'EV-2026-CDC-01',
      title: 'Continuous CDC Stream Watermark Log',
      artifact_type: 'WATERMARK_LOG',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
      producer_authority: 'ReplicationBridgeService',
      fingerprint: '6b5a4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b',
      byte_size: 8388608,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      dossier_id: 'DOS-2026-001',
      certificate_id: 'CERT-MIG-2026-001',
      report_id: 'REP-2026-0101',
      deep_link_route: '/reports/evidence'
    },
    {
      id: 'EV-2026-VAL-02',
      title: 'Relational Constraint Scan Report',
      artifact_type: 'INTEGRITY_SCAN',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 62).toISOString(),
      producer_authority: 'ValidationAssuranceEngine',
      fingerprint: '8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b',
      byte_size: 524288,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      dossier_id: 'DOS-2026-001',
      certificate_id: 'CERT-VAL-2026-002',
      report_id: 'REP-2026-0101',
      deep_link_route: '/reports/evidence'
    },
    {
      id: 'EV-2026-MIG-03',
      title: 'Snowflake Stage Ingestion Manifest',
      artifact_type: 'MANIFEST_SNAPSHOT',
      subject_name: 'Enterprise Data Lakehouse',
      subject_id: 'mig-ent-analytics',
      created_at: new Date(Date.now() - 1000 * 60 * 185).toISOString(),
      producer_authority: 'AKAAL Analytics Bridge',
      fingerprint: '3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c',
      byte_size: 90177536,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      dossier_id: 'DOS-2026-002',
      certificate_id: 'CERT-MIG-2026-003',
      report_id: 'REP-2026-0104',
      deep_link_route: '/reports/evidence'
    },
    {
      id: 'EV-2026-VAL-04',
      title: 'CRM Validation Discrepancy Manifest',
      artifact_type: 'INTEGRITY_SCAN',
      subject_name: 'Customer CRM Database',
      subject_id: 'val-crm-01',
      created_at: new Date(Date.now() - 1000 * 60 * 245).toISOString(),
      producer_authority: 'ValidationAssuranceEngine',
      fingerprint: '7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b',
      byte_size: 131072,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      report_id: 'REP-2026-0102',
      deep_link_route: '/reports/evidence'
    },
    {
      id: 'EV-2026-SCH-01',
      title: 'Oracle to PostgreSQL AST Conformance Diff',
      artifact_type: 'SCHEMA_DIFF',
      subject_name: 'Core Banking Modernization',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 300).toISOString(),
      producer_authority: 'SchemaCompatibilityEvaluator',
      fingerprint: '5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d',
      byte_size: 2097152,
      lifecycle: 'ACTIVE',
      integrity_status: 'VERIFIED',
      dossier_id: 'DOS-2026-001',
      report_id: 'REP-2026-0102',
      deep_link_route: '/reports/evidence'
    }
  ]);

  public dossiers = signal<DossierDTO[]>([
    {
      id: 'DOS-2026-001',
      title: 'Core Banking Ledger Migration Execution Dossier',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      domain: 'MIGRATION & VALIDATION',
      description: 'Consolidated proof collection comprising extraction manifests, Merkle validation roots, dual-control sign-off records, CDC watermark logs, and AST diffs.',
      created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      evidence_count: 5,
      lifecycle: 'ACTIVE',
      evidence_items: []
    },
    {
      id: 'DOS-2026-002',
      title: 'Enterprise Lakehouse Ingestion Audit Dossier',
      subject_name: 'Enterprise Data Lakehouse',
      subject_id: 'mig-ent-analytics',
      domain: 'ANALYTICS INGESTION',
      description: 'Analytical dataset partition manifests and Parquet serialization conformance proof documents.',
      created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
      evidence_count: 1,
      lifecycle: 'ACTIVE',
      evidence_items: []
    }
  ]);

  public certificateArtifacts = signal<CertificateArtifactDTO[]>([
    {
      id: 'CERT-MIG-2026-001',
      title: 'Core Banking Ledger Migration Execution Certification',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      domain: 'MIGRATION',
      issued_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      producer_authority: 'MigrationAssuranceEngine',
      certification_id: 'CERT-MIG-2026-001',
      decision: 'CERTIFIED',
      fingerprint: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
      evidence_refs: ['EV-2026-MIG-01', 'EV-2026-VAL-01', 'EV-2026-GOV-01'],
      download_supported: true
    },
    {
      id: 'CERT-VAL-2026-002',
      title: 'Dual-Engine Reconciliation & Hash Parity Certification',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      domain: 'VALIDATION',
      issued_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      producer_authority: 'ValidationAssuranceEngine',
      certification_id: 'CERT-VAL-2026-002',
      decision: 'CERTIFIED',
      fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
      evidence_refs: ['EV-2026-VAL-01', 'EV-2026-VAL-02'],
      download_supported: true
    },
    {
      id: 'CERT-MIG-2026-003',
      title: 'Snowflake Data Lakehouse Batch Snapshot Certification',
      subject_name: 'Enterprise Data Lakehouse',
      subject_id: 'mig-ent-analytics',
      domain: 'MIGRATION',
      issued_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
      producer_authority: 'MigrationAssuranceEngine',
      certification_id: 'CERT-MIG-2026-003',
      decision: 'CERTIFIED',
      fingerprint: '3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c',
      evidence_refs: ['EV-2026-MIG-03'],
      download_supported: true
    }
  ]);

  public evidencePackages = signal<EvidencePackageDTO[]>([
    {
      id: 'PKG-2026-001',
      title: 'Core Banking Migration Complete Audit & Verification Package',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      status: 'READY',
      generated_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      fingerprint: '1f2e3d4c5b6a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e',
      byte_size: 16777216,
      download_supported: true,
      manifest_items: [
        {
          id: 'pkg-item-01',
          file_name: 'partition_manifest.json',
          artifact_type: 'MANIFEST_SNAPSHOT',
          byte_size: 4194304,
          fingerprint: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
          integrity_status: 'VERIFIED'
        },
        {
          id: 'pkg-item-02',
          file_name: 'merkle_root.digest',
          artifact_type: 'MERKLE_TREE_DIGEST',
          byte_size: 1048576,
          fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
          integrity_status: 'VERIFIED'
        },
        {
          id: 'pkg-item-03',
          file_name: 'governance_signoff.json',
          artifact_type: 'GOVERNANCE_LEDGER',
          byte_size: 262144,
          fingerprint: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
          integrity_status: 'VERIFIED'
        },
        {
          id: 'pkg-item-04',
          file_name: 'cdc_watermarks.log',
          artifact_type: 'WATERMARK_LOG',
          byte_size: 8388608,
          fingerprint: '6b5a4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b',
          integrity_status: 'VERIFIED'
        }
      ]
    },
    {
      id: 'PKG-2026-002',
      title: 'Analytics Data Lakehouse Batch Proof Archive',
      subject_name: 'Enterprise Data Lakehouse',
      subject_id: 'mig-ent-analytics',
      status: 'READY',
      generated_at: new Date(Date.now() - 1000 * 60 * 150).toISOString(),
      fingerprint: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
      byte_size: 94371840,
      download_supported: true,
      manifest_items: [
        {
          id: 'pkg-item-11',
          file_name: 'snowflake_stage_manifest.json',
          artifact_type: 'MANIFEST_SNAPSHOT',
          byte_size: 90177536,
          fingerprint: '3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c',
          integrity_status: 'VERIFIED'
        }
      ]
    }
  ]);

  private _evidenceEnvelopes = signal<Record<string, EvidenceDetailEnvelopeDTO>>({
    'EV-2026-MIG-01': {
      id: 'EV-2026-MIG-01',
      title: 'Partition Bulk Transfer Manifest',
      artifact_type: 'MANIFEST_SNAPSHOT',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 50).toISOString(),
      producer_authority: 'MigrationAssuranceEngine v2.4',
      summary: 'Canonical partition-level extraction manifest recording row-count acknowledgment across 32 partition chunks representing 14.2M records.',
      scope: {
        tenant: 'Production Enterprise',
        workspace: 'Core Banking Modernization',
        project_name: 'Core Banking Modernization',
        migration_name: 'Core Banking Ledger Migration',
        run_id: 'RUN-20260911-001',
        plan_version: 'v4.2-final',
        time_window_start: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
        time_window_end: new Date(Date.now() - 1000 * 60 * 50).toISOString(),
        target_object_scope: '142 tables across 32 partition blocks'
      },
      provenance: {
        producer_authority: 'MigrationAssuranceEngine v2.4',
        created_at: new Date(Date.now() - 1000 * 60 * 50).toISOString(),
        subject_context: 'Core Banking Ledger Migration Stage 3 Partition Extract',
        run_or_plan_binding: 'RUN-20260911-001 / PLAN-v4.2',
        canonical_reference: 'akaal://manifests/mig-core-banking-01/partition_manifest_v1.json'
      },
      integrity: {
        fingerprint: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',
        fingerprint_algorithm: 'SHA-256',
        verification_status: 'VERIFIED',
        verification_method: 'SHA-256 Digest Match',
        verified_at: new Date(Date.now() - 1000 * 60 * 40).toISOString()
      },
      raw_content_preview: JSON.stringify({
        manifest_version: '1.0',
        total_partitions: 32,
        total_rows: 14200000,
        acknowledgment_status: 'ALL_PARTITIONS_COMMITTED',
        digest: '4a8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a'
      }, null, 2),
      related_dossier_ids: ['DOS-2026-001'],
      related_certificate_ids: ['CERT-MIG-2026-001'],
      related_report_ids: ['REP-2026-0101'],
      download_supported: true,
      download_file_name: 'EV-2026-MIG-01-partition-manifest.json'
    },
    'EV-2026-VAL-01': {
      id: 'EV-2026-VAL-01',
      title: 'Dual-Engine Validation Merkle Root Digest',
      artifact_type: 'MERKLE_TREE_DIGEST',
      subject_name: 'Core Banking Ledger Migration',
      subject_id: 'mig-core-banking-01',
      created_at: new Date(Date.now() - 1000 * 60 * 48).toISOString(),
      producer_authority: 'ValidationAssuranceEngine v3.1',
      summary: 'Merkle tree root digest generated from dual-engine row-level checksum tree comparing Oracle 19c and target PostgreSQL 16.',
      scope: {
        tenant: 'Production Enterprise',
        workspace: 'Core Banking Modernization',
        project_name: 'Core Banking Modernization',
        validation_name: 'Dual-Engine Parity Validation',
        run_id: 'RUN-20260911-001',
        time_window_start: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
        target_object_scope: '142 tables, 14.2M rows'
      },
      provenance: {
        producer_authority: 'ValidationAssuranceEngine v3.1',
        created_at: new Date(Date.now() - 1000 * 60 * 48).toISOString(),
        subject_context: 'Dual-Engine Merkle Tree Computation',
        run_or_plan_binding: 'RUN-20260911-001',
        canonical_reference: 'akaal://validation/val-core-banking-01/merkle_root.digest'
      },
      integrity: {
        fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
        fingerprint_algorithm: 'SHA-256',
        verification_status: 'VERIFIED',
        verification_method: 'Merkle Root Match',
        verified_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
        merkle_root: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e'
      },
      raw_content_preview: JSON.stringify({
        merkle_root: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
        leaf_nodes_count: 142000,
        hash_algorithm: 'SHA-256',
        discrepancy_count: 0
      }, null, 2),
      related_dossier_ids: ['DOS-2026-001'],
      related_certificate_ids: ['CERT-VAL-2026-002'],
      related_report_ids: ['REP-2026-0101'],
      download_supported: true,
      download_file_name: 'EV-2026-VAL-01-merkle-digest.json'
    }
  });

  public selectedEvidenceEnvelope = computed<EvidenceDetailEnvelopeDTO | null>(() => {
    const id = this.selectedEvidenceId();
    if (!id) return null;
    return this._evidenceEnvelopes()[id] || this.createFallbackEnvelope(id);
  });

  public selectedDossier = computed<DossierDTO | null>(() => {
    const id = this.selectedDossierId();
    if (!id) return null;
    const found = this.dossiers().find(d => d.id === id);
    if (!found) return null;
    return {
      ...found,
      evidence_items: this.evidenceItems().filter(e => e.dossier_id === found.id)
    };
  });

  public selectedCertificateArtifact = computed<CertificateArtifactDTO | null>(() => {
    const id = this.selectedCertArtifactId();
    if (!id) return null;
    return this.certificateArtifacts().find(c => c.id === id) || null;
  });

  public selectedEvidencePackage = computed<EvidencePackageDTO | null>(() => {
    const id = this.selectedPackageId();
    if (!id) return null;
    return this.evidencePackages().find(p => p.id === id) || null;
  });

  public paginatedEvidence = computed<PaginatedResult<EvidenceItemDTO>>(() => {
    const filters = this.evidenceFilters();
    let list = this.evidenceItems();

    if (filters.search_query && filters.search_query.trim()) {
      const q = filters.search_query.toLowerCase();
      list = list.filter(e => 
        e.title.toLowerCase().includes(q) ||
        e.subject_name.toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q)
      );
    }

    if (filters.artifact_type && filters.artifact_type !== 'ALL') {
      list = list.filter(e => e.artifact_type === filters.artifact_type);
    }

    // Sort
    list = [...list].sort((a, b) => {
      const dir = filters.sort_direction === 'asc' ? 1 : -1;
      if (filters.sort_field === 'title') {
        return a.title.localeCompare(b.title) * dir;
      }
      return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * dir;
    });

    const total_count = list.length;
    const page_size = filters.page_size || 10;
    const total_pages = Math.ceil(total_count / page_size) || 1;
    const start = filters.page_index * page_size;
    const items = list.slice(start, start + page_size);

    return {
      items,
      total_count,
      page_index: filters.page_index,
      page_size,
      total_pages
    };
  });

  private createFallbackEnvelope(id: string): EvidenceDetailEnvelopeDTO {
    const basic = this.evidenceItems().find(e => e.id === id);
    if (basic) {
      return {
        id: basic.id,
        title: basic.title,
        artifact_type: basic.artifact_type,
        subject_name: basic.subject_name,
        subject_id: basic.subject_id,
        created_at: basic.created_at,
        producer_authority: basic.producer_authority,
        summary: `Canonical evidence proof generated by ${basic.producer_authority} for ${basic.subject_name}.`,
        scope: {
          project_name: basic.subject_name,
          migration_name: basic.subject_name
        },
        provenance: {
          producer_authority: basic.producer_authority,
          created_at: basic.created_at,
          subject_context: basic.subject_name,
          canonical_reference: `akaal://evidence/${basic.id}`
        },
        integrity: {
          fingerprint: basic.fingerprint,
          fingerprint_algorithm: 'SHA-256',
          verification_status: basic.integrity_status || 'VERIFIED',
          verification_method: 'SHA-256 Digest Match',
          verified_at: basic.created_at
        },
        related_dossier_ids: basic.dossier_id ? [basic.dossier_id] : [],
        related_certificate_ids: basic.certificate_id ? [basic.certificate_id] : [],
        related_report_ids: basic.report_id ? [basic.report_id] : [],
        download_supported: true,
        download_file_name: `${basic.id}-proof.json`
      };
    }

    return {
      id,
      title: `Evidence Artifact ${id}`,
      artifact_type: 'MANIFEST_SNAPSHOT',
      subject_name: 'Target Subject',
      subject_id: 'unknown-subject',
      created_at: new Date().toISOString(),
      producer_authority: 'System Ledger',
      summary: `Evidence record ${id} retrieved from canonical evidence manifest.`,
      integrity: {
        verification_status: 'NOT_EVALUATED'
      }
    };
  }

  public setEvidenceTab(tab: EvidenceTabMode): void {
    this.activeEvidenceTab.set(tab);
    this.selectedEvidenceId.set(null);
  }

  public updateEvidenceFilter(partial: Partial<EvidencePaginationQuery>): void {
    this.evidenceFilters.update(curr => ({ ...curr, ...partial }));
  }

  public openEvidenceDetail(id: string): void {
    this.selectedEvidenceId.set(id);
  }

  public clearSelectedEvidence(): void {
    this.selectedEvidenceId.set(null);
  }

  public selectDossier(id: string): void {
    this.selectedDossierId.set(id);
    this.activeEvidenceTab.set('DOSSIERS');
  }

  public clearSelectedDossier(): void {
    this.selectedDossierId.set(null);
  }

  public selectCertificateArtifact(id: string): void {
    this.selectedCertArtifactId.set(id);
    this.activeEvidenceTab.set('CERTIFICATES');
  }

  public clearSelectedCertificateArtifact(): void {
    this.selectedCertArtifactId.set(null);
  }

  public selectEvidencePackage(id: string): void {
    this.selectedPackageId.set(id);
    this.activeEvidenceTab.set('PACKAGES');
  }

  public clearSelectedEvidencePackage(): void {
    this.selectedPackageId.set(null);
  }

  public downloadDossierBundle(id: string): void {
    console.log(`[Contextual Export] Downloading dossier bundle for ${id}`);
  }

  public downloadEvidenceArtifact(id: string): void {
    console.log(`[Contextual Export] Downloading evidence proof ${id}`);
  }

  public downloadPackageZip(id: string): void {
    console.log(`[Contextual Export] Downloading package ZIP for ${id}`);
  }

  public verifyArtifactTarget(targetId: string): void {
    // 1. Check in packages
    const pkg = this.evidencePackages().find(p => p.id === targetId);
    if (pkg && pkg.fingerprint) {
      const res: VerificationResultDTO = {
        target_identifier: targetId,
        target_type: 'EVIDENCE_ARTIFACT',
        method: 'SHA-256 Digest Match',
        result_status: 'VERIFIED',
        verified_at: new Date().toISOString(),
        stored_fingerprint: pkg.fingerprint,
        computed_fingerprint: pkg.fingerprint,
        detail_notes: `Package ZIP archive SHA-256 digest verified against package manifest index for '${pkg.title}'.`
      };
      this.activeVerificationResult.set(res);
      this.verificationHistory.update(list => [res, ...list.slice(0, 9)]);
      this.activeCertTab.set('VERIFICATION');
      this.activeEvidenceTab.set('VERIFICATION');
      return;
    }

    // 2. Check in certificate artifacts
    const certArt = this.certificateArtifacts().find(c => c.id === targetId);
    if (certArt && certArt.fingerprint) {
      const res: VerificationResultDTO = {
        target_identifier: targetId,
        target_type: 'CERTIFICATION',
        method: 'SHA-256 Digest Match',
        result_status: 'VERIFIED',
        verified_at: new Date().toISOString(),
        stored_fingerprint: certArt.fingerprint,
        computed_fingerprint: certArt.fingerprint,
        detail_notes: `Stored SHA-256 digest verified against certificate artifact '${certArt.title}'.`
      };
      this.activeVerificationResult.set(res);
      this.verificationHistory.update(list => [res, ...list.slice(0, 9)]);
      this.activeCertTab.set('VERIFICATION');
      this.activeEvidenceTab.set('VERIFICATION');
      return;
    }

    // 3. Check in evidence items
    const evItem = this.evidenceItems().find(e => e.id === targetId);
    if (evItem && evItem.fingerprint) {
      const res: VerificationResultDTO = {
        target_identifier: targetId,
        target_type: 'EVIDENCE_ARTIFACT',
        method: 'SHA-256 Digest Match',
        result_status: evItem.integrity_status === 'VERIFIED' ? 'VERIFIED' : (evItem.integrity_status === 'MISMATCH' ? 'MISMATCH' : 'UNAVAILABLE'),
        verified_at: new Date().toISOString(),
        stored_fingerprint: evItem.fingerprint,
        computed_fingerprint: evItem.fingerprint,
        detail_notes: `Stored SHA-256 digest matches evidence proof artifact '${evItem.title}'.`
      };
      this.activeVerificationResult.set(res);
      this.verificationHistory.update(list => [res, ...list.slice(0, 9)]);
      this.activeCertTab.set('VERIFICATION');
      this.activeEvidenceTab.set('VERIFICATION');
      return;
    }

    // 4. Check in certification envelopes
    const cert = this._certEnvelopes()[targetId];
    if (cert) {
      const res: VerificationResultDTO = {
        target_identifier: targetId,
        target_type: 'CERTIFICATION',
        method: cert.integrity.verification_method,
        result_status: cert.integrity.verification_status === 'VERIFIED' ? 'VERIFIED' : (cert.integrity.verification_status === 'MISMATCH' ? 'MISMATCH' : 'UNAVAILABLE'),
        verified_at: new Date().toISOString(),
        stored_fingerprint: cert.integrity.sha256_fingerprint,
        computed_fingerprint: cert.integrity.sha256_fingerprint,
        detail_notes: `Stored SHA-256 fingerprint verified against canonical ${cert.domain.toLowerCase()} certification envelope.`
      };
      this.activeVerificationResult.set(res);
      this.verificationHistory.update(list => [res, ...list.slice(0, 9)]);
      this.activeCertTab.set('VERIFICATION');
      this.activeEvidenceTab.set('VERIFICATION');
      return;
    }

    // Default: Target could not be resolved
    const res: VerificationResultDTO = {
      target_identifier: targetId,
      target_type: 'EVIDENCE_ARTIFACT',
      method: 'SHA-256 Digest Match',
      result_status: 'UNAVAILABLE',
      verified_at: new Date().toISOString(),
      detail_notes: `Target identifier '${targetId}' could not be resolved against canonical evidence proofs or manifests.`
    };
    this.activeVerificationResult.set(res);
    this.verificationHistory.update(list => [res, ...list.slice(0, 9)]);
    this.activeCertTab.set('VERIFICATION');
    this.activeEvidenceTab.set('VERIFICATION');
  }
}
