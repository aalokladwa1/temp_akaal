/**
 * validation-results.fixtures.ts
 * =====================================
 * Hostile verification fixtures for Workspace 4: Results & Evidence.
 * 
 * Strict Isolation:
 * These fixtures are for automated testing, screenshot generation, and
 * visual verification. Production state initializes strictly to truthful
 * NOT_CONNECTED / NOT_EVALUATED default without synthetic data.
 */

import { ResultsWorkspaceState } from './validation-results.models';

export const FIXTURE_NOT_CONNECTED: ResultsWorkspaceState = {
  viewStatus: 'NOT_EVALUATED',
  isProductionDefault: true,
  isTechnicalDrawerOpen: false,
  validationId: 'val-pending-0000',
  validationName: 'Standby Validation Mission',
  verdict: 'NOT_EVALUATED',
  comparisonMode: 'UNKNOWN',
  temporalModel: 'UNSPECIFIED',
  executionState: 'NOT_CONNECTED',
  baselineState: 'NOT_AVAILABLE',
  verdictSummaryNote: 'Validation Mission is configured but has not completed execution.',
  source: {
    provider: 'Source Endpoint',
    label: 'Not connected',
    host: 'unassigned'
  },
  target: {
    provider: 'Target Endpoint',
    label: 'Not connected',
    host: 'unassigned'
  },
  assuranceTiers: [
    {
      level: 'STRUCTURAL',
      tierNumber: 1,
      title: 'Structural Assurance',
      description: 'Schema compatibility, column count, nullability, and primary key definition.',
      status: 'NOT_EVALUATED',
      evaluatedScopeSummary: '0 of 0 objects evaluated',
      details: 'Awaiting execution'
    },
    {
      level: 'CARDINALITY',
      tierNumber: 2,
      title: 'Cardinality Assurance',
      description: 'Exact and bounded row count matching across selected tables and partitions.',
      status: 'NOT_EVALUATED',
      evaluatedScopeSummary: '0 of 0 objects evaluated',
      details: 'Awaiting execution'
    },
    {
      level: 'PARTITION_FINGERPRINT',
      tierNumber: 3,
      title: 'Partition Fingerprint Assurance',
      description: 'Deterministic partition-level comparison using canonical row fingerprints.',
      status: 'NOT_EVALUATED',
      evaluatedScopeSummary: '0 of 0 objects evaluated',
      details: 'Awaiting execution'
    },
    {
      level: 'COMPLETE_ATTRIBUTE',
      tierNumber: 4,
      title: 'Complete Attribute Assurance',
      description: 'Exhaustive logical value comparison for attributes within the validated scope.',
      status: 'NOT_EVALUATED',
      evaluatedScopeSummary: '0 of 0 objects evaluated',
      details: 'Awaiting execution'
    }
  ],
  unresolvedFindings: null,
  remediationLineage: {
    hasRemediationHistory: false
  },
  runs: [],
  evidence: {
    evidenceAvailable: false,
    integrityNote: 'Evidence bundle has not been generated.'
  },
  auditTimeline: [],
  artifacts: {
    generationAvailable: false,
    availabilityNotice: 'Artifact generation is not currently available.',
    artifacts: []
  },
  technicalDetails: {
    canonicalValidationId: 'val-pending-0000',
    enginePlacement: 'Fabric standby',
    engineVersion: 'v2.4.0-standalone',
    workerCount: null
  }
};

export const RESULTS_FIXTURES: Record<string, ResultsWorkspaceState> = {
  // 1. PASSED + SYNC
  'PASSED_SYNC': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'PASSED_SYNC',
    validationId: 'val-sync-9901',
    validationName: 'Core Banking Ledger Validation',
    verdict: 'PASSED',
    comparisonMode: 'SYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T14:22:10Z',
    durationFormatted: '4m 18s',
    operator: 'm.desai@akaal.internal',
    verdictSummaryNote: 'Validation #11 established complete identity across all 4 assurance tiers under Consistent-State validation mode.',
    source: {
      provider: 'PostgreSQL 16.2',
      label: 'pg_prod_primary',
      host: 'pg-prod-01.us-east-1.internal',
      objectCount: 48
    },
    target: {
      provider: 'Snowflake Enterprise',
      label: 'snow_analytics_raw',
      host: 'xy12345.snowflakecomputing.com',
      objectCount: 48
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '48 of 48 tables evaluated',
        details: 'All columns, constraints, and data types match canonical mappings without variance.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'PASSED',
        evaluatedScopeSummary: '48 of 48 tables evaluated (14.2M rows)',
        details: 'Exact row count parity confirmed across all 48 tables.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'PASSED',
        evaluatedScopeSummary: '384 of 384 partitions evaluated',
        details: 'Deterministic partition fingerprints match between source and target.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'PASSED',
        evaluatedScopeSummary: '48 of 48 tables evaluated (100% attribute scope)',
        details: 'Logical value equivalence verified across all evaluated attributes.'
      }
    ],
    unresolvedFindings: null,
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [
      {
        runId: 'RUN-9901-01',
        trigger: 'MANUAL',
        startedAt: '2026-09-07T14:17:52Z',
        completedAt: '2026-09-07T14:22:10Z',
        durationFormatted: '4m 18s',
        verdict: 'PASSED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 48,
        unresolvedCount: 0,
        operator: 'm.desai@akaal.internal'
      }
    ],
    selectedRunId: 'RUN-9901-01',
    evidence: {
      evidenceAvailable: true,
      evidenceBundleId: 'aev_892f3a91',
      contentDigest: 'sha256:d8e8fca2348a1937402859124018258102938475019283740591827364059182',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T14:22:15Z',
      bundleSizeBytes: 1482049,
      bundleSizeFormatted: '1.41 MB',
      integrityNote: 'Content integrity digest recorded for immutable execution provenance.',
      storageLocation: 's3://akaal-evidence-store/missions/val-sync-9901/aev_892f3a91.bin'
    },
    auditTimeline: [
      {
        id: 'evt-1',
        timestamp: '2026-09-07T14:17:52Z',
        actor: 'm.desai@akaal.internal',
        category: 'VALIDATION',
        title: 'Validation Mission Started',
        description: 'Operator initiated Consistent-State validation against 48 in-scope tables.'
      },
      {
        id: 'evt-2',
        timestamp: '2026-09-07T14:18:30Z',
        actor: 'Engine Worker #1',
        category: 'SYSTEM',
        title: 'Structural & Cardinality Proof Passed',
        description: '48 tables verified for schema compatibility and row count alignment.'
      },
      {
        id: 'evt-3',
        timestamp: '2026-09-07T14:21:40Z',
        actor: 'Engine Worker #4',
        category: 'SYSTEM',
        title: 'Partition Fingerprint & Attribute Proof Passed',
        description: '384 partition fingerprints verified with zero divergent rows.'
      },
      {
        id: 'evt-4',
        timestamp: '2026-09-07T14:22:10Z',
        actor: 'Validation #11 Authority',
        category: 'VALIDATION',
        title: 'Final Verdict: PASSED',
        description: 'Validation #11 declared final PASSED status across full evaluated scope.'
      },
      {
        id: 'evt-5',
        timestamp: '2026-09-07T14:22:15Z',
        actor: 'Evidence #12 Authority',
        category: 'EVIDENCE',
        title: 'Content Integrity Digest Recorded',
        description: 'Evidence bundle created and SHA-256 content digest computed.'
      }
    ],
    artifacts: {
      generationAvailable: true,
      artifacts: [
        {
          id: 'art-1',
          name: 'Execution Summary Report',
          format: 'PDF',
          description: 'Formal operational validation conclusion and tier breakdown.',
          ready: true
        },
        {
          id: 'art-2',
          name: 'Canonical Result Manifest',
          format: 'JSON',
          description: 'Machine-readable validation metadata and tier outcome descriptors.',
          ready: true
        },
        {
          id: 'art-3',
          name: 'Partition Hash Ledger',
          format: 'CSV',
          description: 'Deterministic partition fingerprint proof table.',
          ready: true
        }
      ]
    },
    technicalDetails: {
      canonicalValidationId: 'val-sync-9901',
      planId: 'plan-sync-ledger-48',
      planFingerprint: 'fp_a982bc4410',
      enginePlacement: 'us-east-1-worker-pool-a',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 8,
      p7bFabric: {
        site: 'us-east-1',
        region: 'aws-primary',
        placementNode: 'node-compute-084',
        failoverReady: true
      },
      contentDigest: 'sha256:d8e8fca2348a1937402859124018258102938475019283740591827364059182',
      checkpointReference: 'chk_pt_09182390_sync',
      storageLocation: 's3://akaal-evidence-store/missions/val-sync-9901/aev_892f3a91.bin'
    }
  },

  // 2. FAILED + SYNC (With unresolved findings & evidence available)
  'FAILED_SYNC': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'FAILED_SYNC',
    validationId: 'val-sync-9902',
    validationName: 'Payment Settlement Reconciliation',
    verdict: 'FAILED',
    comparisonMode: 'SYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T15:10:45Z',
    durationFormatted: '3m 42s',
    operator: 's.sharma@akaal.internal',
    verdictSummaryNote: 'Validation #11 completed execution and detected 142 unresolved discrepancies across 3 tables.',
    source: {
      provider: 'Oracle Database 19c',
      label: 'ora_settlement_db',
      host: 'settlement-db.corp.internal:1521',
      objectCount: 24
    },
    target: {
      provider: 'PostgreSQL 16.2',
      label: 'pg_settlement_replica',
      host: 'pg-replica-02.internal:5432',
      objectCount: 24
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '24 of 24 tables evaluated',
        details: 'Schema structures match exactly across all 24 evaluated entities.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'FAILED',
        evaluatedScopeSummary: '24 of 24 tables evaluated',
        details: 'Row count mismatch detected in settlement_ledger (Delta: -112 rows).'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'FAILED',
        evaluatedScopeSummary: '192 partitions evaluated',
        details: '3 divergent partition fingerprints discovered in transaction_batches.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'FAILED',
        evaluatedScopeSummary: '24 of 24 tables evaluated',
        details: 'Attribute discrepancies discovered in fee_amount and settlement_status fields.'
      }
    ],
    unresolvedFindings: {
      totalCount: 142,
      affectedObjectsCount: 3,
      affectedCategories: ['Row Count Variance', 'Partition Fingerprint Mismatch', 'Attribute Value Divergence'],
      sampleObjects: ['settlement_ledger', 'transaction_batches', 'fee_allocations'],
      discrepanciesTabTarget: 'discrepancies'
    },
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [
      {
        runId: 'RUN-9902-01',
        trigger: 'MANUAL',
        startedAt: '2026-09-07T15:07:03Z',
        completedAt: '2026-09-07T15:10:45Z',
        durationFormatted: '3m 42s',
        verdict: 'FAILED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 24,
        unresolvedCount: 142,
        operator: 's.sharma@akaal.internal'
      }
    ],
    selectedRunId: 'RUN-9902-01',
    evidence: {
      evidenceAvailable: true,
      evidenceBundleId: 'aev_failed_4401',
      contentDigest: 'sha256:4901824701982734091823091823091823091820391823091823091823091823',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T15:10:50Z',
      bundleSizeBytes: 842100,
      bundleSizeFormatted: '822.4 KB',
      integrityNote: 'Content integrity digest recorded for audit verification.'
    },
    auditTimeline: [
      {
        id: 'evt-101',
        timestamp: '2026-09-07T15:07:03Z',
        actor: 's.sharma@akaal.internal',
        category: 'VALIDATION',
        title: 'Validation Mission Started',
        description: 'Consistent-State validation triggered on settlement tables.'
      },
      {
        id: 'evt-102',
        timestamp: '2026-09-07T15:09:12Z',
        actor: 'Engine Worker #2',
        category: 'SYSTEM',
        title: 'Discrepancies Detected',
        description: 'Cardinality and attribute variances identified in settlement_ledger.'
      },
      {
        id: 'evt-103',
        timestamp: '2026-09-07T15:10:45Z',
        actor: 'Validation #11 Authority',
        category: 'VALIDATION',
        title: 'Final Verdict: FAILED',
        description: 'Validation #11 concluded with FAILED verdict due to 142 unresolved discrepancies.'
      },
      {
        id: 'evt-104',
        timestamp: '2026-09-07T15:10:50Z',
        actor: 'Evidence #12 Authority',
        category: 'EVIDENCE',
        title: 'Content Integrity Digest Recorded',
        description: 'Evidence bundle containing discrepancy records preserved with SHA-256 digest.'
      }
    ],
    artifacts: {
      generationAvailable: true,
      artifacts: [
        {
          id: 'art-f1',
          name: 'Discrepancy Investigation Manifest',
          format: 'CSV',
          description: 'Catalog of 142 unresolved row differences for remediation review.',
          ready: true
        }
      ]
    },
    technicalDetails: {
      canonicalValidationId: 'val-sync-9902',
      enginePlacement: 'us-west-2-worker-pool-b',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 4,
      contentDigest: 'sha256:4901824701982734091823091823091823091820391823091823091823091823'
    }
  },

  // 3. PASSED + ASYNC
  'PASSED_ASYNC': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'PASSED_ASYNC',
    validationId: 'val-async-3011',
    validationName: 'Customer Analytics Lakehouse Sync',
    verdict: 'PASSED',
    comparisonMode: 'ASYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T12:00:15Z',
    durationFormatted: '8m 20s',
    operator: 'k.patel@akaal.internal',
    verdictSummaryNote: 'Validation #11 verified asynchronous batch snapshot against source baseline with zero variances.',
    source: {
      provider: 'MySQL 8.0',
      label: 'mysql_cust_db',
      host: 'mysql-prod.internal:3306',
      objectCount: 64
    },
    target: {
      provider: 'Google BigQuery',
      label: 'bq_analytics_raw',
      host: 'bigquery.googleapis.com/projects/corp-analytics',
      objectCount: 64
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '64 of 64 tables evaluated',
        details: 'Column types and nullability constraints match snapshot specification.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'PASSED',
        evaluatedScopeSummary: '64 of 64 tables evaluated (28.9M rows)',
        details: 'Asynchronous snapshot row counts match boundary position.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'PASSED',
        evaluatedScopeSummary: '512 partitions evaluated',
        details: 'Deterministic partition fingerprints match canonical baseline.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'PASSED',
        evaluatedScopeSummary: '64 of 64 tables evaluated',
        details: 'Attribute values verified for all in-scope dimensions.'
      }
    ],
    unresolvedFindings: null,
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [
      {
        runId: 'RUN-3011-01',
        trigger: 'SCHEDULED',
        startedAt: '2026-09-07T11:51:55Z',
        completedAt: '2026-09-07T12:00:15Z',
        durationFormatted: '8m 20s',
        verdict: 'PASSED',
        comparisonMode: 'ASYNC',
        evaluatedObjectsCount: 64,
        unresolvedCount: 0,
        operator: 'Scheduler'
      }
    ],
    selectedRunId: 'RUN-3011-01',
    evidence: {
      evidenceAvailable: true,
      evidenceBundleId: 'aev_async_3011',
      contentDigest: 'sha256:8819230491823091823091823091823091823091823091823091823091823091',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T12:00:20Z',
      bundleSizeBytes: 2109400,
      bundleSizeFormatted: '2.01 MB',
      integrityNote: 'Content integrity digest recorded for asynchronous batch validation run.'
    },
    auditTimeline: [
      {
        id: 'evt-201',
        timestamp: '2026-09-07T11:51:55Z',
        actor: 'Scheduled Job',
        category: 'VALIDATION',
        title: 'Validation Mission Started',
        description: 'Automated batch comparison executed on daily snapshot.'
      },
      {
        id: 'evt-202',
        timestamp: '2026-09-07T12:00:15Z',
        actor: 'Validation #11 Authority',
        category: 'VALIDATION',
        title: 'Final Verdict: PASSED',
        description: 'Validation #11 confirmed complete snapshot identity.'
      }
    ],
    artifacts: {
      generationAvailable: true,
      artifacts: []
    },
    technicalDetails: {
      canonicalValidationId: 'val-async-3011',
      enginePlacement: 'us-east-1-batch-pool',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 6,
      contentDigest: 'sha256:8819230491823091823091823091823091823091823091823091823091823091'
    }
  },

  // 4. FAILED + ASYNC
  'FAILED_ASYNC': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'FAILED_ASYNC',
    validationId: 'val-async-3012',
    validationName: 'Product Catalog Replica Check',
    verdict: 'FAILED',
    comparisonMode: 'ASYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T09:40:00Z',
    durationFormatted: '2m 14s',
    operator: 'k.patel@akaal.internal',
    verdictSummaryNote: 'Validation #11 detected 8 discrepancies in asynchronous replica snapshot.',
    source: {
      provider: 'PostgreSQL 15.4',
      label: 'pg_catalog_master',
      host: 'catalog-master.internal:5432',
      objectCount: 16
    },
    target: {
      provider: 'PostgreSQL 15.4',
      label: 'pg_catalog_read_replica',
      host: 'catalog-replica-eu.internal:5432',
      objectCount: 16
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '16 of 16 tables evaluated',
        details: 'Schemas are fully compatible.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'PASSED',
        evaluatedScopeSummary: '16 of 16 tables evaluated',
        details: 'Row counts align across all tables.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'FAILED',
        evaluatedScopeSummary: '64 partitions evaluated',
        details: '1 divergent partition fingerprint identified in product_skus.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'FAILED',
        evaluatedScopeSummary: '16 of 16 tables evaluated',
        details: '8 attribute value differences found in inventory_quantity.'
      }
    ],
    unresolvedFindings: {
      totalCount: 8,
      affectedObjectsCount: 1,
      affectedCategories: ['Partition Fingerprint Mismatch', 'Attribute Value Divergence'],
      sampleObjects: ['product_skus'],
      discrepanciesTabTarget: 'discrepancies'
    },
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [
      {
        runId: 'RUN-3012-01',
        trigger: 'MANUAL',
        startedAt: '2026-09-07T09:37:46Z',
        completedAt: '2026-09-07T09:40:00Z',
        durationFormatted: '2m 14s',
        verdict: 'FAILED',
        comparisonMode: 'ASYNC',
        evaluatedObjectsCount: 16,
        unresolvedCount: 8,
        operator: 'k.patel@akaal.internal'
      }
    ],
    selectedRunId: 'RUN-3012-01',
    evidence: {
      evidenceAvailable: true,
      contentDigest: 'sha256:1928374019283740192837401928374019283740192837401928374019283740',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T09:40:05Z',
      bundleSizeBytes: 240100,
      bundleSizeFormatted: '234.5 KB',
      integrityNote: 'Content integrity digest recorded for audit verification.'
    },
    auditTimeline: [],
    artifacts: {
      generationAvailable: false,
      availabilityNotice: 'Artifact generation is not currently available for this run.',
      artifacts: []
    },
    technicalDetails: {
      canonicalValidationId: 'val-async-3012',
      enginePlacement: 'eu-central-1-worker',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 2,
      contentDigest: 'sha256:1928374019283740192837401928374019283740192837401928374019283740'
    }
  },

  // 5. REMEDIATED_REVALIDATED_PASSED (Immutable History: Initial Fail -> Repair -> Reval Pass)
  'REMEDIATED_REVALIDATED_PASSED': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'REMEDIATED_REVALIDATED_PASSED',
    validationId: 'val-rem-8810',
    validationName: 'Inventory Master Replication & Repair',
    verdict: 'PASSED',
    comparisonMode: 'SYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T16:30:10Z',
    durationFormatted: '1m 45s (Reval)',
    operator: 'lead.dba@akaal.internal',
    verdictSummaryNote: 'Validation #11 revalidated scope following Controlled Repair RP-881 and verified complete resolution with zero remaining discrepancies.',
    source: {
      provider: 'Microsoft SQL Server 2022',
      label: 'mssql_inv_master',
      host: 'sql-inv-01.corp.internal',
      objectCount: 32
    },
    target: {
      provider: 'PostgreSQL 16.2',
      label: 'pg_inv_warehouse',
      host: 'pg-warehouse-01.internal',
      objectCount: 32
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '32 of 32 tables evaluated',
        details: 'Structural integrity confirmed.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'PASSED',
        evaluatedScopeSummary: '32 of 32 tables evaluated (4.8M rows)',
        details: 'Row counts match exactly after repair upsert.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'PASSED',
        evaluatedScopeSummary: '128 partitions evaluated',
        details: 'All partition fingerprints matching following repair.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'PASSED',
        evaluatedScopeSummary: '32 of 32 tables evaluated',
        details: 'All attribute values validated against canonical source truth.'
      }
    ],
    unresolvedFindings: null,
    remediationLineage: {
      hasRemediationHistory: true,
      initialValidation: {
        runId: 'RUN-8810-01',
        verdict: 'FAILED',
        timestamp: '2026-09-07T14:00:00Z',
        discrepancyCount: 18
      },
      controlledRemediation: {
        repairPlanId: 'RP-881',
        strategy: 'Target Upsert from Authoritative Source',
        executedAt: '2026-09-07T15:20:00Z',
        status: 'COMPLETED',
        operationsCount: 18
      },
      revalidation: {
        runId: 'RUN-8810-02',
        verdict: 'PASSED',
        completedAt: '2026-09-07T16:30:10Z',
        remainingDiscrepancies: 0,
        notes: 'Validation #11 confirmed complete discrepancy resolution across all evaluated tables.'
      }
    },
    runs: [
      {
        runId: 'RUN-8810-02',
        trigger: 'REVALIDATION',
        startedAt: '2026-09-07T16:28:25Z',
        completedAt: '2026-09-07T16:30:10Z',
        durationFormatted: '1m 45s',
        verdict: 'PASSED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 32,
        unresolvedCount: 0,
        operator: 'lead.dba@akaal.internal'
      },
      {
        runId: 'RUN-8810-01',
        trigger: 'MANUAL',
        startedAt: '2026-09-07T13:55:00Z',
        completedAt: '2026-09-07T14:00:00Z',
        durationFormatted: '5m 00s',
        verdict: 'FAILED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 32,
        unresolvedCount: 18,
        operator: 'lead.dba@akaal.internal'
      }
    ],
    selectedRunId: 'RUN-8810-02',
    evidence: {
      evidenceAvailable: true,
      evidenceBundleId: 'aev_rem_8810',
      contentDigest: 'sha256:fa90128304918230918230918230918230918230918230918230918230918230',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T16:30:15Z',
      bundleSizeBytes: 981200,
      bundleSizeFormatted: '958.2 KB',
      integrityNote: 'Content integrity digest recorded for revalidation conclusion.'
    },
    auditTimeline: [
      {
        id: 'evt-r1',
        timestamp: '2026-09-07T14:00:00Z',
        actor: 'Validation #11 Authority',
        category: 'VALIDATION',
        title: 'Initial Validation Failed',
        description: '18 discrepancies identified in warehouse inventory balances.'
      },
      {
        id: 'evt-r2',
        timestamp: '2026-09-07T15:20:00Z',
        actor: 'lead.dba@akaal.internal',
        category: 'REMEDIATION',
        title: 'Controlled Repair Executed (RP-881)',
        description: 'Target upsert applied 18 mutations under operator authorization.'
      },
      {
        id: 'evt-r3',
        timestamp: '2026-09-07T16:30:10Z',
        actor: 'Validation #11 Authority',
        category: 'VALIDATION',
        title: 'Revalidation Succeeded (Verdict: PASSED)',
        description: 'Validation #11 verified all 32 tables with 0 remaining discrepancies.'
      }
    ],
    artifacts: {
      generationAvailable: true,
      artifacts: [
        {
          id: 'art-rem-1',
          name: 'Remediation & Revalidation Audit Trail',
          format: 'PDF',
          description: 'Formal audit document linking initial failure, repair authorization, and revalidation pass.',
          ready: true
        }
      ]
    },
    technicalDetails: {
      canonicalValidationId: 'val-rem-8810',
      enginePlacement: 'us-east-1-worker-pool-a',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 4,
      contentDigest: 'sha256:fa90128304918230918230918230918230918230918230918230918230918230'
    }
  },

  // 6. REMEDIATED_REVALIDATION_FAILED (Initial Fail -> Repair -> Reval Failed)
  'REMEDIATED_REVALIDATION_FAILED': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'REMEDIATED_REVALIDATION_FAILED',
    validationId: 'val-rem-8811',
    validationName: 'Customer Profile Replication',
    verdict: 'FAILED',
    comparisonMode: 'SYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T17:15:00Z',
    durationFormatted: '2m 10s (Reval)',
    operator: 'lead.dba@akaal.internal',
    verdictSummaryNote: 'Validation #11 revalidated scope following Controlled Repair RP-882 but found 3 remaining discrepancies.',
    source: {
      provider: 'PostgreSQL 16.2',
      label: 'pg_cust_primary',
      host: 'pg-cust-01.internal',
      objectCount: 12
    },
    target: {
      provider: 'Snowflake Enterprise',
      label: 'snow_cust_dw',
      host: 'corp.snowflakecomputing.com',
      objectCount: 12
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '12 of 12 tables evaluated',
        details: 'Structural integrity confirmed.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'FAILED',
        evaluatedScopeSummary: '12 of 12 tables evaluated',
        details: 'Row count mismatch persists in customer_addresses (Delta: -3 rows).'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'FAILED',
        evaluatedScopeSummary: '48 partitions evaluated',
        details: '1 divergent partition fingerprint remaining.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'FAILED',
        evaluatedScopeSummary: '12 of 12 tables evaluated',
        details: 'Attribute discrepancies discovered in postal_code.'
      }
    ],
    unresolvedFindings: {
      totalCount: 3,
      affectedObjectsCount: 1,
      affectedCategories: ['Row Count Variance', 'Partition Fingerprint Mismatch'],
      sampleObjects: ['customer_addresses'],
      discrepanciesTabTarget: 'discrepancies'
    },
    remediationLineage: {
      hasRemediationHistory: true,
      initialValidation: {
        runId: 'RUN-8811-01',
        verdict: 'FAILED',
        timestamp: '2026-09-07T15:00:00Z',
        discrepancyCount: 15
      },
      controlledRemediation: {
        repairPlanId: 'RP-882',
        strategy: 'Target Upsert from Authoritative Source',
        executedAt: '2026-09-07T16:45:00Z',
        status: 'COMPLETED',
        operationsCount: 12
      },
      revalidation: {
        runId: 'RUN-8811-02',
        verdict: 'FAILED',
        completedAt: '2026-09-07T17:15:00Z',
        remainingDiscrepancies: 3,
        notes: '3 discrepancies remain unresolved after remediation.'
      }
    },
    runs: [
      {
        runId: 'RUN-8811-02',
        trigger: 'REVALIDATION',
        startedAt: '2026-09-07T17:12:50Z',
        completedAt: '2026-09-07T17:15:00Z',
        durationFormatted: '2m 10s',
        verdict: 'FAILED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 12,
        unresolvedCount: 3,
        operator: 'lead.dba@akaal.internal'
      }
    ],
    selectedRunId: 'RUN-8811-02',
    evidence: {
      evidenceAvailable: true,
      contentDigest: 'sha256:7719283049182309182309182309182309182309182309182309182309182309',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T17:15:05Z',
      bundleSizeBytes: 310400,
      bundleSizeFormatted: '303.1 KB',
      integrityNote: 'Content integrity digest recorded for revalidation outcome.'
    },
    auditTimeline: [],
    artifacts: {
      generationAvailable: false,
      availabilityNotice: 'Artifact generation is not currently available.',
      artifacts: []
    },
    technicalDetails: {
      canonicalValidationId: 'val-rem-8811',
      enginePlacement: 'us-east-1-worker-pool-a',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 2,
      contentDigest: 'sha256:7719283049182309182309182309182309182309182309182309182309182309'
    }
  },

  // 7. UNKNOWN_RELATIONSHIP_MODE
  'UNKNOWN_RELATIONSHIP_MODE': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'UNKNOWN_RELATIONSHIP_MODE',
    validationId: 'val-unk-1099',
    validationName: 'Staging Partition Assessment',
    verdict: 'PASSED',
    comparisonMode: 'UNKNOWN',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'NOT_AVAILABLE',
    completedAt: '2026-09-07T13:00:00Z',
    durationFormatted: '1m 12s',
    operator: 'j.doe@akaal.internal',
    verdictSummaryNote: 'Validation #11 confirmed identity across evaluated tables. Relationship mode unspecified in engine metadata.',
    source: {
      provider: 'Generic JDBC Source',
      label: 'stage_src_db',
      host: 'stage-db-01.internal:3306',
      objectCount: 8
    },
    target: {
      provider: 'Generic JDBC Target',
      label: 'stage_tgt_db',
      host: 'stage-db-02.internal:3306',
      objectCount: 8
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '8 of 8 tables evaluated',
        details: 'Structural compatibility confirmed.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'PASSED',
        evaluatedScopeSummary: '8 of 8 tables evaluated',
        details: 'Row count match verified.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'PASSED',
        evaluatedScopeSummary: '32 partitions evaluated',
        details: 'Partition fingerprints match.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'PASSED',
        evaluatedScopeSummary: '8 of 8 tables evaluated',
        details: 'Attribute equivalence confirmed.'
      }
    ],
    unresolvedFindings: null,
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [],
    evidence: {
      evidenceAvailable: false,
      integrityNote: 'Evidence bundle not generated.'
    },
    auditTimeline: [],
    artifacts: {
      generationAvailable: false,
      availabilityNotice: 'Artifact generation is not currently available.',
      artifacts: []
    },
    technicalDetails: {
      canonicalValidationId: 'val-unk-1099',
      enginePlacement: 'local-test-fabric',
      engineVersion: 'v2.4.0-standalone'
    }
  },

  // 8. WITHHELD
  'WITHHELD': {
    viewStatus: 'WITHHELD',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'WITHHELD',
    validationId: 'val-withheld-5501',
    validationName: 'High Concurrency Order Processing',
    verdict: 'WITHHELD',
    comparisonMode: 'SYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'INTERRUPTED',
    baselineState: 'STALE',
    completedAt: '2026-09-07T11:15:30Z',
    durationFormatted: '1m 05s (Withheld)',
    operator: 'sys.governance@akaal.internal',
    verdictSummaryNote: 'Validation #11 withheld verdict: Source write boundary violated read-consistency lease during evaluation.',
    source: {
      provider: 'PostgreSQL 16.2',
      label: 'pg_orders_live',
      host: 'orders-primary.corp.internal',
      objectCount: 18
    },
    target: {
      provider: 'Snowflake Enterprise',
      label: 'snow_orders_raw',
      host: 'corp.snowflakecomputing.com',
      objectCount: 18
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '18 of 18 tables evaluated',
        details: 'Schema evaluation succeeded.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'NOT_EVALUATED',
        evaluatedScopeSummary: 'Evaluated paused',
        details: 'Withheld due to unrecoverable read boundary drift on live source.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'NOT_EVALUATED',
        evaluatedScopeSummary: 'Evaluated paused',
        details: 'Withheld due to unrecoverable read boundary drift.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'NOT_EVALUATED',
        evaluatedScopeSummary: 'Evaluated paused',
        details: 'Withheld due to unrecoverable read boundary drift.'
      }
    ],
    unresolvedFindings: null,
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [],
    evidence: {
      evidenceAvailable: false,
      integrityNote: 'Evidence bundle not generated for withheld execution.'
    },
    auditTimeline: [
      {
        id: 'evt-w1',
        timestamp: '2026-09-07T11:15:30Z',
        actor: 'Validation #11 Authority',
        category: 'VALIDATION',
        title: 'Verdict Withheld by Validation #11',
        description: 'Consistency window lease expired during read evaluation.'
      }
    ],
    artifacts: {
      generationAvailable: false,
      availabilityNotice: 'Artifact generation is not currently available.',
      artifacts: []
    },
    technicalDetails: {
      canonicalValidationId: 'val-withheld-5501',
      enginePlacement: 'us-east-1-worker-pool-a',
      engineVersion: 'v2.4.0-standalone'
    }
  },

  // 9. 40M UNRESOLVED FINDINGS (Testing massive aggregate format)
  'HIGH_VOLUME_40M_FINDINGS': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'HIGH_VOLUME_40M_FINDINGS',
    validationId: 'val-scale-40m',
    validationName: 'Telecom Call Detail Records (CDR) Validation',
    verdict: 'FAILED',
    comparisonMode: 'ASYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T08:30:00Z',
    durationFormatted: '42m 10s',
    operator: 'telecom.eng@akaal.internal',
    verdictSummaryNote: 'Validation #11 completed validation on 1.2B rows and discovered 40,000,000 divergent record fingerprints across 12 partition tables.',
    source: {
      provider: 'Oracle Exadata',
      label: 'ora_cdr_prod',
      host: 'exadata-cdr-01.telecom.internal',
      objectCount: 12
    },
    target: {
      provider: 'Google BigQuery',
      label: 'bq_cdr_warehouse',
      host: 'bigquery.googleapis.com/projects/cdr-analytics',
      objectCount: 12
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '12 of 12 tables evaluated',
        details: 'Structural definitions aligned.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'FAILED',
        evaluatedScopeSummary: '12 of 12 tables evaluated (1.2B rows)',
        details: 'Cardinality mismatch: 40,000,000 row differential detected across partitions.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'FAILED',
        evaluatedScopeSummary: '1,440 partitions evaluated',
        details: '48 divergent partition fingerprints.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'FAILED',
        evaluatedScopeSummary: '12 of 12 tables evaluated',
        details: 'Differences found in call_duration_seconds and roaming_charge_cents.'
      }
    ],
    unresolvedFindings: {
      totalCount: 40000000,
      affectedObjectsCount: 12,
      affectedCategories: ['Partition Fingerprint Mismatch', 'Row Count Variance', 'Attribute Value Divergence'],
      sampleObjects: ['cdr_voice_2026_09', 'cdr_data_sessions', 'roaming_records'],
      discrepanciesTabTarget: 'discrepancies'
    },
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [
      {
        runId: 'RUN-40M-01',
        trigger: 'SCHEDULED',
        startedAt: '2026-09-07T07:47:50Z',
        completedAt: '2026-09-07T08:30:00Z',
        durationFormatted: '42m 10s',
        verdict: 'FAILED',
        comparisonMode: 'ASYNC',
        evaluatedObjectsCount: 12,
        unresolvedCount: 40000000,
        operator: 'telecom.eng@akaal.internal'
      }
    ],
    selectedRunId: 'RUN-40M-01',
    evidence: {
      evidenceAvailable: true,
      evidenceBundleId: 'aev_cdr_40m',
      contentDigest: 'sha256:6618293049182309182309182309182309182309182309182309182309182309',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T08:30:15Z',
      bundleSizeBytes: 18491024,
      bundleSizeFormatted: '17.63 MB',
      integrityNote: 'Content integrity digest recorded for large-scale reconciliation audit.'
    },
    auditTimeline: [],
    artifacts: {
      generationAvailable: false,
      availabilityNotice: 'Artifact generation is not currently available for high-volume datasets.',
      artifacts: []
    },
    technicalDetails: {
      canonicalValidationId: 'val-scale-40m',
      enginePlacement: 'big-data-cluster-c',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 32,
      contentDigest: 'sha256:6618293049182309182309182309182309182309182309182309182309182309'
    }
  },

  // 10. MULTIPLE_HISTORICAL_RUNS
  'MULTIPLE_HISTORICAL_RUNS': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'MULTIPLE_HISTORICAL_RUNS',
    validationId: 'val-runs-1080',
    validationName: 'Financial Data Mart Recurring Audit',
    verdict: 'PASSED',
    comparisonMode: 'SYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T18:00:00Z',
    durationFormatted: '3m 15s',
    operator: 'audit.lead@akaal.internal',
    verdictSummaryNote: 'Validation #11 evaluated Run #05 and established complete identity with 0 discrepancies.',
    source: {
      provider: 'Oracle Database 19c',
      label: 'ora_fin_mart',
      host: 'fin-mart.corp.internal',
      objectCount: 20
    },
    target: {
      provider: 'Snowflake Enterprise',
      label: 'snow_fin_dw',
      host: 'corp.snowflakecomputing.com',
      objectCount: 20
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '20 of 20 tables evaluated',
        details: 'Structural compatibility confirmed.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'PASSED',
        evaluatedScopeSummary: '20 of 20 tables evaluated (6.4M rows)',
        details: 'Exact row count parity verified.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'PASSED',
        evaluatedScopeSummary: '160 partitions evaluated',
        details: 'Partition fingerprints matching.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'PASSED',
        evaluatedScopeSummary: '20 of 20 tables evaluated',
        details: 'Attribute equivalence verified.'
      }
    ],
    unresolvedFindings: null,
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [
      {
        runId: 'RUN-1080-05',
        trigger: 'SCHEDULED',
        startedAt: '2026-09-07T17:56:45Z',
        completedAt: '2026-09-07T18:00:00Z',
        durationFormatted: '3m 15s',
        verdict: 'PASSED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 20,
        unresolvedCount: 0,
        operator: 'Scheduler'
      },
      {
        runId: 'RUN-1080-04',
        trigger: 'SCHEDULED',
        startedAt: '2026-09-06T18:00:10Z',
        completedAt: '2026-09-06T18:03:30Z',
        durationFormatted: '3m 20s',
        verdict: 'PASSED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 20,
        unresolvedCount: 0,
        operator: 'Scheduler'
      },
      {
        runId: 'RUN-1080-03',
        trigger: 'MANUAL',
        startedAt: '2026-09-05T14:10:00Z',
        completedAt: '2026-09-05T14:14:12Z',
        durationFormatted: '4m 12s',
        verdict: 'FAILED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 20,
        unresolvedCount: 4,
        operator: 'audit.lead@akaal.internal'
      },
      {
        runId: 'RUN-1080-02',
        trigger: 'SCHEDULED',
        startedAt: '2026-09-04T18:00:00Z',
        completedAt: '2026-09-04T18:03:15Z',
        durationFormatted: '3m 15s',
        verdict: 'PASSED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 20,
        unresolvedCount: 0,
        operator: 'Scheduler'
      },
      {
        runId: 'RUN-1080-01',
        trigger: 'MANUAL',
        startedAt: '2026-09-03T09:00:00Z',
        completedAt: '2026-09-03T09:04:00Z',
        durationFormatted: '4m 00s',
        verdict: 'PASSED',
        comparisonMode: 'SYNC',
        evaluatedObjectsCount: 20,
        unresolvedCount: 0,
        operator: 'audit.lead@akaal.internal'
      }
    ],
    selectedRunId: 'RUN-1080-05',
    evidence: {
      evidenceAvailable: true,
      contentDigest: 'sha256:5519283049182309182309182309182309182309182309182309182309182309',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T18:00:05Z',
      bundleSizeBytes: 890100,
      bundleSizeFormatted: '869.2 KB',
      integrityNote: 'Content integrity digest recorded for scheduled audit execution.'
    },
    auditTimeline: [],
    artifacts: {
      generationAvailable: true,
      artifacts: [
        {
          id: 'art-h1',
          name: 'Run History Summary Ledger',
          format: 'CSV',
          description: 'Historical summary of all 5 validation runs.',
          ready: true
        }
      ]
    },
    technicalDetails: {
      canonicalValidationId: 'val-runs-1080',
      enginePlacement: 'us-east-1-worker-pool-a',
      engineVersion: 'v2.4.0-standalone',
      workerCount: 4,
      contentDigest: 'sha256:5519283049182309182309182309182309182309182309182309182309182309'
    }
  },

  // 11. LONG_IDENTIFIERS (Hostile UI wrapping test)
  'LONG_IDENTIFIERS': {
    viewStatus: 'READY',
    isProductionDefault: false,
    isTechnicalDrawerOpen: false,
    activeScenarioId: 'LONG_IDENTIFIERS',
    validationId: 'val-long-identifier-very-extended-uuid-99019283-0192-3847-5019-283740591827-corp-enterprise-prod-system',
    validationName: 'Enterprise Core Account Receivable and Cross Border Settlement Currency Hedging Multi Partition Table Synchronization Mission',
    verdict: 'PASSED',
    comparisonMode: 'SYNC',
    temporalModel: 'CONSISTENT_STATE',
    executionState: 'COMPLETED',
    baselineState: 'VALID',
    completedAt: '2026-09-07T14:22:10Z',
    durationFormatted: '12m 45s',
    operator: 'principal.database.reliability.engineer.lead@subdivision.regional.enterprise.akaal.internal',
    verdictSummaryNote: 'Validation #11 verified all entities across extended identifiers.',
    source: {
      provider: 'Amazon Aurora PostgreSQL Compatible Engine 16.2 Enterprise Edition',
      label: 'aurora_prod_primary_instance_cluster_us_east_1a_read_write_node_01',
      host: 'aurora-pg-cluster-prod-enterprise-01.c7x89q2k.us-east-1.rds.amazonaws.com:5432',
      objectCount: 128
    },
    target: {
      provider: 'Snowflake Enterprise Multi-Cluster Data Warehouse Architecture',
      label: 'snow_dw_corporate_financial_settlement_curated_lakehouse_zone_raw',
      host: 'corporate-enterprise-finance-data-platform-us-east-1.privatelink.snowflakecomputing.com',
      objectCount: 128
    },
    assuranceTiers: [
      {
        level: 'STRUCTURAL',
        tierNumber: 1,
        title: 'Structural Assurance',
        description: 'Schema compatibility, column count, nullability, and primary key definition.',
        status: 'PASSED',
        evaluatedScopeSummary: '128 of 128 tables evaluated',
        details: 'Structural compatibility confirmed.'
      },
      {
        level: 'CARDINALITY',
        tierNumber: 2,
        title: 'Cardinality Assurance',
        description: 'Exact and bounded row count matching across selected tables and partitions.',
        status: 'PASSED',
        evaluatedScopeSummary: '128 of 128 tables evaluated',
        details: 'Row counts match.'
      },
      {
        level: 'PARTITION_FINGERPRINT',
        tierNumber: 3,
        title: 'Partition Fingerprint Assurance',
        description: 'Deterministic partition-level comparison using canonical row fingerprints.',
        status: 'PASSED',
        evaluatedScopeSummary: '1,024 partitions evaluated',
        details: 'Partition fingerprints match.'
      },
      {
        level: 'COMPLETE_ATTRIBUTE',
        tierNumber: 4,
        title: 'Complete Attribute Assurance',
        description: 'Exhaustive logical value comparison for attributes within the validated scope.',
        status: 'PASSED',
        evaluatedScopeSummary: '128 of 128 tables evaluated',
        details: 'Attribute values match.'
      }
    ],
    unresolvedFindings: null,
    remediationLineage: {
      hasRemediationHistory: false
    },
    runs: [],
    evidence: {
      evidenceAvailable: true,
      contentDigest: 'sha256:d8e8fca2348a1937402859124018258102938475019283740591827364059182',
      digestAlgorithm: 'SHA-256',
      generatedAt: '2026-09-07T14:22:15Z',
      bundleSizeBytes: 4890100,
      bundleSizeFormatted: '4.66 MB',
      integrityNote: 'Content integrity digest recorded.'
    },
    auditTimeline: [],
    artifacts: {
      generationAvailable: false,
      availabilityNotice: 'Artifact generation is not currently available.',
      artifacts: []
    },
    technicalDetails: {
      canonicalValidationId: 'val-long-identifier-very-extended-uuid-99019283-0192-3847-5019-283740591827-corp-enterprise-prod-system',
      enginePlacement: 'us-east-1-dedicated-vpc-subnet-az1-fabric-node-0994',
      engineVersion: 'v2.4.0-standalone',
      contentDigest: 'sha256:d8e8fca2348a1937402859124018258102938475019283740591827364059182'
    }
  }
};
