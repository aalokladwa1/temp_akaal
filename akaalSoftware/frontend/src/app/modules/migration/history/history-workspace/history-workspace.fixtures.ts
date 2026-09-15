/**
 * AKAAL Migration History Workspace Presentation Fixtures
 * 
 * Comprehensive, mode-aware, internally consistent enterprise records spanning all
 * 8 Modes (M1-M8), multiple runs, multi-approver quorum, timeline events, validation
 * discrepancies, cutover chronologies, checkpoint lineages, evidence manifests, and
 * hash-chained audit trails.
 */

import { MigrationHistoryWorkspaceRecord } from './history-workspace.models';

export const HISTORY_WORKSPACE_FIXTURES: Record<string, MigrationHistoryWorkspaceRecord> = {
  // ===========================================================================
  // SCENARIO B: M2 Bulk + CDC (Core Financial Transaction Ledger)
  // ===========================================================================
  'mig-fin-core-01': {
    id: 'mig-fin-core-01',
    migrationId: 'mig-fin-core-01',
    migrationName: 'Core Financial Transaction Ledger Migration',
    executionId: 'exec-20260908-0842',
    projectId: 'proj-fin-core',
    projectName: 'Financial Core Modernization',
    initiativeName: 'Global Ledger Modernization 2026',
    sourceProvider: 'Oracle Database 19c Enterprise',
    sourceProviderCode: 'oracle',
    targetProvider: 'PostgreSQL 16.2 Cloud Native',
    targetProviderCode: 'postgres',
    mode: 'M2_BULK_CDC',
    outcome: 'SUCCEEDED',
    lifecycleState: 'COMPLETED',
    startedAt: '2026-09-08T01:30:00Z',
    completedAt: '2026-09-08T06:12:38Z',
    durationString: '4h 42m 38s',
    totalRowsProcessed: 38450120,
    throughputFormatted: '54,200 rows/s',
    errorMessage: null,
    operator: 'A. Ladwa (Lead DBA)',
    materialExceptions: [],
    
    // 1. Timeline
    timeline: [
      {
        id: 'tl-001',
        timestamp: '2026-09-08T01:00:00Z',
        title: 'Plan Initialized & Fingerprinted',
        description: 'Execution plan plan-fin-2026-v2 compiled with SHA-256 fingerprint sha256:d82f91...',
        category: 'PLANNING',
        severity: 'INFO',
        actor: 'A. Ladwa (Lead DBA)'
      },
      {
        id: 'tl-002',
        timestamp: '2026-09-08T01:15:00Z',
        title: 'Production Governance Barrier Quorum Satisfied',
        description: 'Multi-approver quorum (2/2) satisfied by Security Officer and VP Infrastructure.',
        category: 'GOVERNANCE',
        severity: 'SUCCESS',
        actor: 'Quorum Governance Engine'
      },
      {
        id: 'tl-003',
        timestamp: '2026-09-08T01:30:00Z',
        title: 'Execution Stage 1 (Initial Bulk Load) Started',
        description: 'Parallel partition extraction initialized across 16 database worker threads.',
        category: 'EXECUTION',
        severity: 'INFO',
        actor: 'Pipeline Engine'
      },
      {
        id: 'tl-004',
        timestamp: '2026-09-08T04:45:00Z',
        title: 'Initial Bulk Snapshot Complete (38.45M Rows)',
        description: 'Bulk phase completed with zero row drops. Streaming CDC replication attached at SCN 91048291.',
        category: 'EXECUTION',
        severity: 'SUCCESS',
        actor: 'Pipeline Engine'
      },
      {
        id: 'tl-005',
        timestamp: '2026-09-08T05:30:00Z',
        title: 'Pre-Cutover Forensic Validation Passed',
        description: 'Deep checksum parity check completed with 0 discrepancies across all ledger tables.',
        category: 'VALIDATION',
        severity: 'SUCCESS',
        actor: 'Validation Engine'
      },
      {
        id: 'tl-006',
        timestamp: '2026-09-08T06:05:00Z',
        title: 'Live Cutover Gate Opened',
        description: 'Final CDC synchronization lag reduced to 0.0s. Target promotion authorized.',
        category: 'CONTINUITY',
        severity: 'SUCCESS',
        actor: 'A. Ladwa (Lead DBA)'
      },
      {
        id: 'tl-007',
        timestamp: '2026-09-08T06:12:38Z',
        title: 'Target Cutover Completed & Evidence Sealed',
        description: 'Target PostgreSQL promoted to primary ledger. Cryptographic SHA-256 evidence manifest sealed.',
        category: 'LIFECYCLE',
        severity: 'SUCCESS',
        actor: 'System Orchestrator'
      }
    ],

    // 2. Execution Runs & Stages
    executionRuns: [
      {
        runId: 'run-001',
        executionId: 'exec-20260908-0842',
        runNumber: 1,
        outcome: 'SUCCEEDED',
        startedAt: '2026-09-08T01:30:00Z',
        completedAt: '2026-09-08T06:12:38Z',
        duration: '4h 42m 38s',
        totalRowsProcessed: 38450120,
        totalBytesProcessed: '42.8 GB',
        avgThroughput: '54,200 rows/s',
        cdcBacklogSeconds: 0.0,
        cdcEventsProcessed: 148920,
        watermarkProgression: 'SCN 91048291 → SCN 91197211',
        errorMessage: null,
        attempts: [
          {
            attemptNumber: 1,
            invocationId: 'inv-001-a1',
            state: 'SUCCEEDED',
            startedAt: '2026-09-08T01:30:00Z',
            completedAt: '2026-09-08T06:12:38Z',
            duration: '4h 42m 38s',
            errorReason: null,
            checkpointResumeId: 'chk-init-01',
            fenceEpoch: 1
          }
        ],
        stages: [
          {
            id: 'stg-1',
            name: 'Schema Verification & Target Table Prep',
            stageType: 'DDL_APPLY',
            status: 'COMPLETED',
            startedAt: '2026-09-08T01:30:00Z',
            completedAt: '2026-09-08T01:34:10Z',
            duration: '4m 10s',
            rowsIn: 0,
            rowsOut: 0,
            throughput: 'N/A'
          },
          {
            id: 'stg-2',
            name: 'Parallel Bulk Table Extraction (16 Partitions)',
            stageType: 'EXTRACT',
            status: 'COMPLETED',
            startedAt: '2026-09-08T01:34:10Z',
            completedAt: '2026-09-08T04:45:00Z',
            duration: '3h 10m 50s',
            rowsIn: 38450120,
            rowsOut: 38450120,
            throughput: '62,400 rows/s'
          },
          {
            id: 'stg-3',
            name: 'CDC Catch-Up Streaming & Log Ingestion',
            stageType: 'STREAM_CDC',
            status: 'COMPLETED',
            startedAt: '2026-09-08T04:45:00Z',
            completedAt: '2026-09-08T06:05:00Z',
            duration: '1h 20m 00s',
            rowsIn: 148920,
            rowsOut: 148920,
            throughput: '1,860 events/s'
          },
          {
            id: 'stg-4',
            name: 'Final Parity Validation & Evidence Sealing',
            stageType: 'VALIDATE',
            status: 'COMPLETED',
            startedAt: '2026-09-08T06:05:00Z',
            completedAt: '2026-09-08T06:12:38Z',
            duration: '7m 38s',
            rowsIn: 38450120,
            rowsOut: 38450120,
            throughput: '83,900 rows/s'
          }
        ]
      }
    ],

    // 3. Plan & Configuration
    planAndConfig: {
      currentPlanId: 'plan-fin-core-2026-v2',
      planFingerprint: 'sha256:d82f91a04b81029cba48102983ca102948bca019284ca019284bd819203bc910',
      revisions: [
        {
          revisionNumber: 2,
          planId: 'plan-fin-core-2026-v2',
          fingerprint: 'sha256:d82f91a04b81029cba48102983ca102948bca019284ca019284bd819203bc910',
          createdAt: '2026-09-08T00:50:00Z',
          createdBy: 'A. Ladwa (Lead DBA)',
          changeSummary: 'Increased CDC buffer memory to 4096MB and enabled strict Merkle root validation.',
          isCurrentExecutionPlan: true
        },
        {
          revisionNumber: 1,
          planId: 'plan-fin-core-2026-v1',
          fingerprint: 'sha256:77a10293ca019284bd910283ca019284ba019284ca910284ab019284bc910284',
          createdAt: '2026-09-07T16:20:00Z',
          createdBy: 'A. Ladwa (Lead DBA)',
          changeSummary: 'Initial generated plan from financial migration wizard.',
          isCurrentExecutionPlan: false
        }
      ],
      sections: [
        {
          title: 'Scope & Object Selection',
          description: 'Defines targeted schema objects, tables, indexes, and partition filters.',
          entries: [
            { label: 'Source Schema', value: 'FIN_CORE_PROD' },
            { label: 'Target Schema', value: 'public' },
            { label: 'Included Tables', value: 'transactions, accounts, ledger_entries, audit_logs' },
            { label: 'Excluded Tables', value: 'tmp_staging, scratch_reconcile' },
            { label: 'Partition Strategy', value: 'Parallel Range Partitioning (16 Workers)' }
          ]
        },
        {
          title: 'Mapping & Type Conversion',
          description: 'Type mappings and conversion rules between Oracle 19c and PostgreSQL 16.',
          entries: [
            { label: 'NUMBER(18,4)', value: 'NUMERIC(18,4)' },
            { label: 'VARCHAR2(255)', value: 'VARCHAR(255)' },
            { label: 'TIMESTAMP WITH TIME ZONE', value: 'TIMESTAMPTZ' },
            { label: 'CLOB', value: 'TEXT' }
          ]
        },
        {
          title: 'Privacy & Data Protection',
          description: 'PII masking, column exclusion, and tokenization rules applied at ingestion.',
          entries: [
            { label: 'Account Numbers', value: 'Deterministic SHA-256 Salted Tokenization' },
            { label: 'Customer SSN / Tax ID', value: 'Redacted (Masked to Last 4 Digits)' },
            { label: 'Encryption in Transit', value: 'TLS 1.3 Strict Mutual Authentication' }
          ]
        },
        {
          title: 'Runtime & CDC Tuning',
          description: 'Concurrency limits, batch sizing, buffer allocations, and CDC polling rates.',
          entries: [
            { label: 'Batch Commit Size', value: '25,000 Rows / Transaction' },
            { label: 'Worker Concurrency', value: '16 Parallel Threads' },
            { label: 'CDC Buffer Allocation', value: '4,096 MB In-Memory Ring Buffer' },
            { label: 'Lag Threshold Alert', value: '1.0s Max Allowed' }
          ]
        }
      ],
      semanticDiffs: [
        {
          fieldName: 'CDC Buffer Allocation',
          category: 'Runtime Performance',
          oldValue: '1,024 MB',
          newValue: '4,096 MB',
          impactLevel: 'MODERATE'
        },
        {
          fieldName: 'Validation Strategy',
          category: 'Validation',
          oldValue: 'Sampled 10%',
          newValue: '100% Merkle Tree Parity',
          impactLevel: 'CRITICAL'
        }
      ]
    },

    // 4. Governance & Approvals
    governance: [
      {
        barrierId: 'bar-fin-001',
        protectedOperation: 'Production Cutover & Primary Database Re-routing',
        requestedAt: '2026-09-08T01:05:00Z',
        requesterName: 'A. Ladwa (Lead DBA)',
        makerCheckerSatisfied: true,
        quorumRequired: 2,
        quorumSatisfied: 2,
        status: 'APPROVED',
        planFingerprintBinding: 'sha256:d82f91a04b81029cba48102983ca102948bca019284ca019284bd819203bc910',
        expiresAt: '2026-09-08T08:00:00Z',
        approvers: [
          {
            approverName: 'E. Sterling',
            role: 'VP Infrastructure & Operations',
            decision: 'APPROVED',
            decidedAt: '2026-09-08T01:12:00Z',
            comment: 'Production change ticket CHG-8941 approved. Window confirmed.'
          },
          {
            approverName: 'V. Patel',
            role: 'Principal Security Officer',
            decision: 'APPROVED',
            decidedAt: '2026-09-08T01:14:45Z',
            comment: 'Masking specifications and cryptographic seal parameters verified.'
          }
        ],
        decisionNotes: 'All maker-checker dual controls satisfied prior to initial bulk extraction.'
      }
    ],

    // 5. Validation & Reconciliation
    validationRuns: [
      {
        validationRunId: 'val-run-001-post',
        phase: 'POST_MIGRATION',
        startedAt: '2026-09-08T06:05:00Z',
        completedAt: '2026-09-08T06:12:00Z',
        duration: '7m 00s',
        verdict: 'PASSED',
        rowCountSource: 38450120,
        rowCountTarget: 38450120,
        rowCountDelta: 0,
        merkleTreeRootMatch: true,
        discrepancyCount: 0,
        discrepancies: []
      },
      {
        validationRunId: 'val-run-001-pre',
        phase: 'PRE_MIGRATION',
        startedAt: '2026-09-08T01:25:00Z',
        completedAt: '2026-09-08T01:29:40Z',
        duration: '4m 40s',
        verdict: 'PASSED',
        rowCountSource: 38450120,
        rowCountTarget: 0,
        rowCountDelta: 38450120,
        merkleTreeRootMatch: true,
        discrepancyCount: 0,
        discrepancies: []
      }
    ],

    // 6. Cutover & Continuity
    cutover: {
      isApplicableToMode: true,
      cutoverStatus: 'COMPLETED',
      recoveryStatus: 'NONE',
      cutoverPlannedAt: '2026-09-08T06:00:00Z',
      cutoverExecutedAt: '2026-09-08T06:12:00Z',
      downtimeSeconds: 38,
      cdcFinalLagSeconds: 0.0,
      finalSyncCatchupSeconds: 14,
      postCutoverVerificationPassed: true,
      failbackReady: true,
      failbackInvoked: false,
      failbackReason: null,
      chronology: [
        {
          stepName: 'Cutover Gate Verification',
          status: 'COMPLETED',
          timestamp: '2026-09-08T06:00:00Z',
          duration: '1m 20s',
          details: 'Verified replication lag under 0.5s threshold and target database read-only test passed.'
        },
        {
          stepName: 'Source Database Write Quiesce',
          status: 'COMPLETED',
          timestamp: '2026-09-08T06:01:20Z',
          duration: '12s',
          details: 'Oracle source transactions gracefully quiesced and flushed to redo logs.'
        },
        {
          stepName: 'Final CDC Catch-up Drain',
          status: 'COMPLETED',
          timestamp: '2026-09-08T06:01:32Z',
          duration: '14s',
          details: 'Drained remaining 4,210 change records. Final CDC lag reached exactly 0.0s.'
        },
        {
          stepName: 'Target PostgreSQL Role Promotion',
          status: 'COMPLETED',
          timestamp: '2026-09-08T06:01:46Z',
          duration: '12s',
          details: 'Target PostgreSQL database promoted to primary read/write authority.'
        },
        {
          stepName: 'Post-Cutover Parity & Smoke Verification',
          status: 'COMPLETED',
          timestamp: '2026-09-08T06:02:00Z',
          duration: '10m 00s',
          details: 'Post-cutover validation check passed with 100% table and row parity.'
        }
      ]
    },

    // 7. Recovery & Checkpoints
    recovery: {
      hasRecoveryOccurred: false,
      recoveryTriggerReason: null,
      recoveryTriggeredAt: null,
      recoveredAt: null,
      checkpointResumedFrom: null,
      fenceEpoch: 1,
      dataSafetyAttestation: 'All 38,450,120 rows migrated and validated under execution fence epoch 1. Zero data loss or rollbacks.',
      checkpoints: [
        {
          checkpointId: 'chk-fin-001-init',
          generation: 1,
          createdAt: '2026-09-08T01:30:00Z',
          associatedStage: 'Initialization',
          isSelectedForResume: false,
          isSuperseded: true,
          fenceEpoch: 1,
          committedRowsWatermark: 0
        },
        {
          checkpointId: 'chk-fin-002-bulk-mid',
          generation: 2,
          createdAt: '2026-09-08T03:00:00Z',
          associatedStage: 'Bulk Extraction (50%)',
          isSelectedForResume: false,
          isSuperseded: true,
          fenceEpoch: 1,
          committedRowsWatermark: 19225060
        },
        {
          checkpointId: 'chk-fin-003-bulk-end',
          generation: 3,
          createdAt: '2026-09-08T04:45:00Z',
          associatedStage: 'Bulk Phase Complete',
          isSelectedForResume: false,
          isSuperseded: true,
          fenceEpoch: 1,
          committedRowsWatermark: 38450120
        },
        {
          checkpointId: 'chk-fin-004-final-cutover',
          generation: 4,
          createdAt: '2026-09-08T06:12:38Z',
          associatedStage: 'Post-Cutover Sealed',
          isSelectedForResume: true,
          isSuperseded: false,
          fenceEpoch: 1,
          committedRowsWatermark: 38450120
        }
      ],
      residualExceptions: []
    },

    // 8. Evidence & Sealing
    evidence: {
      availability: 'SEALED',
      integrity: 'SHA256_VERIFIED',
      completeness: 'COMPLETE',
      manifests: [
        {
          manifestId: 'man-fin-20260908-01',
          executionId: 'exec-20260908-0842',
          generatedAt: '2026-09-08T06:12:38Z',
          completeness: 'COMPLETE',
          artifactCount: 14,
          totalSizeBytes: 1482094,
          digestVerification: 'SHA256_VERIFIED',
          rootDigestSha256: 'sha256:4f8a92b7c6104e12e34d9a8820c7104b9012fce4d98a02b61405e192a83b1029'
        }
      ],
      artifacts: [
        {
          id: 'art-001',
          category: 'PLAN',
          name: 'execution_plan_snapshot.json',
          digest: 'sha256:d82f91a04b81029cba48102983ca102948bca019284ca019284bd819203bc910',
          recordedAt: '2026-09-08T01:00:00Z',
          verified: true
        },
        {
          id: 'art-002',
          category: 'GOVERNANCE',
          name: 'quorum_approval_attestation.json',
          digest: 'sha256:b10489cf019284ba019284bc910284ab019284ca019284cf910284bd019284',
          recordedAt: '2026-09-08T01:15:00Z',
          verified: true
        },
        {
          id: 'art-003',
          category: 'VALIDATION',
          name: 'merkle_parity_audit_report.json',
          digest: 'sha256:7b10ca89f0183d29a562ce0948b8120d8f0291ba48e104f9810283c76104be12',
          recordedAt: '2026-09-08T06:12:00Z',
          verified: true
        },
        {
          id: 'art-004',
          category: 'CUTOVER',
          name: 'cutover_downtime_attestation.json',
          digest: 'sha256:e90184ba019284cd019284be910284ab019284ca019284cf910284bd019284',
          recordedAt: '2026-09-08T06:12:38Z',
          verified: true
        }
      ],
      identitySeal: {
        sealVersion: 'v1.0.0-PROD',
        fingerprintSha256: 'sha256:4f8a92b7c6104e12e34d9a8820c7104b9012fce4d98a02b61405e192a83b1029',
        fields: [
          { name: 'Migration ID', value: 'mig-fin-core-01' },
          { name: 'Execution ID', value: 'exec-20260908-0842' },
          { name: 'Project Key', value: 'proj-fin-core' },
          { name: 'Initiative Key', value: 'Global Ledger Modernization 2026' },
          { name: 'Source Provider', value: 'Oracle Database 19c Enterprise' },
          { name: 'Target Provider', value: 'PostgreSQL 16.2 Cloud Native' },
          { name: 'Migration Mode', value: 'M2_BULK_CDC' },
          { name: 'Plan Fingerprint', value: 'sha256:d82f91a04b81029cba48102983ca102948bca019284ca019284bd819203bc910' },
          { name: 'Governance Quorum', value: '2/2 Satisfied' },
          { name: 'Validation Verdict', value: 'PASSED (0 Discrepancies)' },
          { name: 'Rows Processed', value: '38,450,120' },
          { name: 'Cutover Status', value: 'COMPLETED (38s Downtime)' },
          { name: 'Operator ID', value: 'A. Ladwa (Lead DBA)' },
          { name: 'Timestamp Started', value: '2026-09-08T01:30:00Z' },
          { name: 'Timestamp Completed', value: '2026-09-08T06:12:38Z' }
        ]
      },
      lastIntegrityCheckAt: '2026-09-08T06:15:00Z',
      integrityVerificationNotes: 'All 14 artifacts match root manifest digest. SHA-256 content integrity verified.'
    },

    // 9. Audit Trail
    auditTrail: [
      {
        id: 'aud-001',
        timestamp: '2026-09-08T00:50:00Z',
        actorPrincipal: 'aladwa@enterprise.corp',
        actorRole: 'Lead DBA',
        action: 'PLAN_REVISION_CREATED',
        resourceTarget: 'plan-fin-core-2026-v2',
        outcome: 'SUCCESS',
        correlationExecutionId: 'exec-20260908-0842',
        beforeSnapshotJson: '{"revision": 1, "cdc_buffer_mb": 1024}',
        afterSnapshotJson: '{"revision": 2, "cdc_buffer_mb": 4096}',
        evidenceRefId: 'art-001',
        hashChainLinkSha256: 'sha256:11a09182ba019284cd019284be910284ab019284ca019284cf910284bd019284'
      },
      {
        id: 'aud-002',
        timestamp: '2026-09-08T01:12:00Z',
        actorPrincipal: 'esterling@enterprise.corp',
        actorRole: 'VP Infrastructure',
        action: 'BARRIER_APPROVAL_GRANTED',
        resourceTarget: 'bar-fin-001',
        outcome: 'SUCCESS',
        correlationExecutionId: 'exec-20260908-0842',
        beforeSnapshotJson: '{"status": "PENDING"}',
        afterSnapshotJson: '{"status": "APPROVED", "quorum": "1/2"}',
        evidenceRefId: 'art-002',
        hashChainLinkSha256: 'sha256:22b09182ba019284cd019284be910284ab019284ca019284cf910284bd019284'
      },
      {
        id: 'aud-003',
        timestamp: '2026-09-08T01:14:45Z',
        actorPrincipal: 'vpatel@enterprise.corp',
        actorRole: 'Principal Security Officer',
        action: 'BARRIER_APPROVAL_GRANTED',
        resourceTarget: 'bar-fin-001',
        outcome: 'SUCCESS',
        correlationExecutionId: 'exec-20260908-0842',
        beforeSnapshotJson: '{"status": "PENDING", "quorum": "1/2"}',
        afterSnapshotJson: '{"status": "APPROVED", "quorum": "2/2"}',
        evidenceRefId: 'art-002',
        hashChainLinkSha256: 'sha256:33c09182ba019284cd019284be910284ab019284ca019284cf910284bd019284'
      },
      {
        id: 'aud-004',
        timestamp: '2026-09-08T06:01:20Z',
        actorPrincipal: 'aladwa@enterprise.corp',
        actorRole: 'Lead DBA',
        action: 'CUTOVER_EXECUTION_TRIGGERED',
        resourceTarget: 'mig-fin-core-01',
        outcome: 'SUCCESS',
        correlationExecutionId: 'exec-20260908-0842',
        beforeSnapshotJson: '{"primary_db": "oracle_source"}',
        afterSnapshotJson: '{"primary_db": "postgres_target"}',
        evidenceRefId: 'art-004',
        hashChainLinkSha256: 'sha256:44d09182ba019284cd019284be910284ab019284ca019284cf910284bd019284'
      },
      {
        id: 'aud-005',
        timestamp: '2026-09-08T06:12:38Z',
        actorPrincipal: 'system_orchestrator@akaal.internal',
        actorRole: 'System Orchestrator',
        action: 'EVIDENCE_MANIFEST_SEALED',
        resourceTarget: 'man-fin-20260908-01',
        outcome: 'SUCCESS',
        correlationExecutionId: 'exec-20260908-0842',
        beforeSnapshotJson: null,
        afterSnapshotJson: '{"root_digest": "sha256:4f8a92b7c6104e12e34d9a8820c7104b9012fce4d98a02b61405e192a83b1029"}',
        evidenceRefId: 'art-003',
        hashChainLinkSha256: 'sha256:55e09182ba019284cd019284be910284ab019284ca019284cf910284bd019284'
      }
    ]
  },

  // ===========================================================================
  // SCENARIO H: M8 Validation Only (Financial Reconciliation & Sync Assurance)
  // ===========================================================================
  'mig-audit-m8-01': {
    id: 'mig-audit-m8-01',
    migrationId: 'mig-audit-m8-01',
    migrationName: 'Q3 Financial Reconciliation & Sync Assurance',
    executionId: 'exec-20260907-1420',
    projectId: 'proj-fin-core',
    projectName: 'Financial Core Modernization',
    initiativeName: 'Global Ledger Modernization 2026',
    sourceProvider: 'Oracle Database 19c Enterprise',
    sourceProviderCode: 'oracle',
    targetProvider: 'PostgreSQL 16.2 Cloud Native',
    targetProviderCode: 'postgres',
    mode: 'M8_VALIDATION_ONLY',
    outcome: 'SUCCEEDED',
    lifecycleState: 'COMPLETED',
    startedAt: '2026-09-07T14:00:00Z',
    completedAt: '2026-09-07T14:48:12Z',
    durationString: '48m 12s',
    totalRowsProcessed: 12450000,
    throughputFormatted: '43,080 rows/s',
    errorMessage: null,
    operator: 'System Automated (Audit Agent)',
    materialExceptions: [],

    timeline: [
      {
        id: 'tl-m8-01',
        timestamp: '2026-09-07T14:00:00Z',
        title: 'M8 Validation Audit Initialized',
        description: 'Deep checksum and Merkle tree verification initialized across 12.45M audited ledger records.',
        category: 'PLANNING',
        severity: 'INFO',
        actor: 'Audit Daemon'
      },
      {
        id: 'tl-m8-02',
        timestamp: '2026-09-07T14:48:12Z',
        title: 'Validation Audit Completed — 0 Discrepancies',
        description: 'Complete data synchronization assurance confirmed with 100% row count and payload parity.',
        category: 'VALIDATION',
        severity: 'SUCCESS',
        actor: 'Validation Engine'
      }
    ],

    executionRuns: [
      {
        runId: 'run-m8-001',
        executionId: 'exec-20260907-1420',
        runNumber: 1,
        outcome: 'SUCCEEDED',
        startedAt: '2026-09-07T14:00:00Z',
        completedAt: '2026-09-07T14:48:12Z',
        duration: '48m 12s',
        totalRowsProcessed: 12450000,
        totalBytesProcessed: '14.2 GB',
        avgThroughput: '43,080 rows/s',
        cdcBacklogSeconds: null,
        cdcEventsProcessed: null,
        watermarkProgression: null,
        errorMessage: null,
        attempts: [
          {
            attemptNumber: 1,
            invocationId: 'inv-m8-001',
            state: 'SUCCEEDED',
            startedAt: '2026-09-07T14:00:00Z',
            completedAt: '2026-09-07T14:48:12Z',
            duration: '48m 12s',
            errorReason: null,
            checkpointResumeId: null,
            fenceEpoch: 1
          }
        ],
        stages: [
          {
            id: 'stg-m8-1',
            name: 'Row Count Parity Probe',
            stageType: 'VALIDATE',
            status: 'COMPLETED',
            startedAt: '2026-09-07T14:00:00Z',
            completedAt: '2026-09-07T14:05:00Z',
            duration: '5m 00s',
            rowsIn: 12450000,
            rowsOut: 12450000,
            throughput: '41,500 rows/s'
          },
          {
            id: 'stg-m8-2',
            name: 'Merkle Tree Hash Payload Verification',
            stageType: 'VALIDATE',
            status: 'COMPLETED',
            startedAt: '2026-09-07T14:05:00Z',
            completedAt: '2026-09-07T14:48:12Z',
            duration: '43m 12s',
            rowsIn: 12450000,
            rowsOut: 12450000,
            throughput: '43,260 rows/s'
          }
        ]
      }
    ],

    planAndConfig: {
      currentPlanId: 'plan-audit-m8-2026',
      planFingerprint: 'sha256:7b10ca89f0183d29a562ce0948b8120d8f0291ba48e104f9810283c76104be12',
      revisions: [
        {
          revisionNumber: 1,
          planId: 'plan-audit-m8-2026',
          fingerprint: 'sha256:7b10ca89f0183d29a562ce0948b8120d8f0291ba48e104f9810283c76104be12',
          createdAt: '2026-09-07T13:50:00Z',
          createdBy: 'Audit Agent',
          changeSummary: 'Scheduled forensic sync audit plan.',
          isCurrentExecutionPlan: true
        }
      ],
      sections: [
        {
          title: 'Validation Scope',
          description: 'M8 Independent Data Synchronization Assurance configuration.',
          entries: [
            { label: 'Mode Type', value: 'M8 • Validation Only' },
            { label: 'Audited Tables', value: 'transactions, ledger_journal' },
            { label: 'Algorithm', value: 'Parallel Merkle Tree Stream Hash' },
            { label: 'Sampling Rate', value: '100% Full Scan (Zero Sampling)' }
          ]
        }
      ],
      semanticDiffs: []
    },

    governance: [],

    validationRuns: [
      {
        validationRunId: 'val-m8-run-01',
        phase: 'POST_MIGRATION',
        startedAt: '2026-09-07T14:00:00Z',
        completedAt: '2026-09-07T14:48:12Z',
        duration: '48m 12s',
        verdict: 'PASSED',
        rowCountSource: 12450000,
        rowCountTarget: 12450000,
        rowCountDelta: 0,
        merkleTreeRootMatch: true,
        discrepancyCount: 0,
        discrepancies: []
      }
    ],

    cutover: {
      isApplicableToMode: false,
      cutoverStatus: 'NOT_APPLICABLE',
      recoveryStatus: 'NOT_APPLICABLE',
      cutoverPlannedAt: null,
      cutoverExecutedAt: null,
      downtimeSeconds: null,
      cdcFinalLagSeconds: null,
      finalSyncCatchupSeconds: null,
      postCutoverVerificationPassed: true,
      failbackReady: false,
      failbackInvoked: false,
      failbackReason: null,
      chronology: []
    },

    recovery: {
      hasRecoveryOccurred: false,
      recoveryTriggerReason: null,
      recoveryTriggeredAt: null,
      recoveredAt: null,
      checkpointResumedFrom: null,
      fenceEpoch: 1,
      dataSafetyAttestation: 'M8 Validation run completed with read-only probe. No target mutation occurred.',
      checkpoints: [],
      residualExceptions: []
    },

    evidence: {
      availability: 'SEALED',
      integrity: 'SHA256_VERIFIED',
      completeness: 'COMPLETE',
      manifests: [
        {
          manifestId: 'man-m8-20260907-01',
          executionId: 'exec-20260907-1420',
          generatedAt: '2026-09-07T14:48:12Z',
          completeness: 'COMPLETE',
          artifactCount: 6,
          totalSizeBytes: 2894102,
          digestVerification: 'SHA256_VERIFIED',
          rootDigestSha256: 'sha256:7b10ca89f0183d29a562ce0948b8120d8f0291ba48e104f9810283c76104be12'
        }
      ],
      artifacts: [
        {
          id: 'art-m8-01',
          category: 'VALIDATION',
          name: 'merkle_audit_tree_digest.json',
          digest: 'sha256:7b10ca89f0183d29a562ce0948b8120d8f0291ba48e104f9810283c76104be12',
          recordedAt: '2026-09-07T14:48:12Z',
          verified: true
        }
      ],
      identitySeal: {
        sealVersion: 'v1.0.0-PROD',
        fingerprintSha256: 'sha256:7b10ca89f0183d29a562ce0948b8120d8f0291ba48e104f9810283c76104be12',
        fields: [
          { name: 'Migration ID', value: 'mig-audit-m8-01' },
          { name: 'Execution ID', value: 'exec-20260907-1420' },
          { name: 'Migration Mode', value: 'M8_VALIDATION_ONLY' },
          { name: 'Validation Verdict', value: 'PASSED' },
          { name: 'Rows Audited', value: '12,450,000' }
        ]
      },
      lastIntegrityCheckAt: '2026-09-07T14:50:00Z',
      integrityVerificationNotes: 'Merkle root hash verification verified without discrepancies.'
    },

    auditTrail: [
      {
        id: 'aud-m8-01',
        timestamp: '2026-09-07T14:00:00Z',
        actorPrincipal: 'audit_daemon@akaal.internal',
        actorRole: 'Audit Daemon',
        action: 'M8_VALIDATION_AUDIT_STARTED',
        resourceTarget: 'mig-audit-m8-01',
        outcome: 'SUCCESS',
        correlationExecutionId: 'exec-20260907-1420',
        beforeSnapshotJson: null,
        afterSnapshotJson: '{"audit_status": "RUNNING"}',
        evidenceRefId: null,
        hashChainLinkSha256: 'sha256:66f09182ba019284cd019284be910284ab019284ca019284cf910284bd019284'
      }
    ]
  }
};
