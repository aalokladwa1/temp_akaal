/**
 * AKAAL Migration History & Evidence Domain Models
 * 
 * Defines canonical data contracts for the Migration History & Evidence Home.
 * Covers all 8 Migration & Assurance Modes (M1-M8), three orthogonal truth dimensions
 * (Execution Outcome, Validation/Reconciliation, Evidence Availability/Integrity),
 * Continuity/Recovery context, and enterprise filtering/sorting state.
 */

export type HistoryMode =
  | 'M1_BULK'           // Bulk Load / Snapshot
  | 'M2_BULK_CDC'       // Bulk + CDC (Initial Snapshot + Ongoing Replication)
  | 'M3_CDC'            // CDC Only (Continuous Streaming)
  | 'M4_INCREMENTAL'    // Incremental / Polling
  | 'M5_STATE_SYNC'     // State-Based Sync (Two-way / Multi-directional)
  | 'M6_SCHEMA_ONLY'    // Schema Only (DDL Extraction & Conversion)
  | 'M7_DATA_ONLY'      // Data Only (No Schema Alteration)
  | 'M8_VALIDATION_ONLY'; // Validation Only (Data Synchronization Assurance)

export interface HistoryModeDescriptor {
  code: HistoryMode;
  shortCode: string;   // "M1", "M2", ..., "M8"
  label: string;       // "Bulk Load", "Bulk + CDC", ..., "Validation Only"
  fullLabel: string;   // "M1 • Bulk Load", ..., "M8 • Validation Only"
  description: string;
  supportsCutover: boolean;
  isValidationAssurance: boolean;
}

export const HISTORY_MODE_DESCRIPTORS: Record<HistoryMode, HistoryModeDescriptor> = {
  M1_BULK: {
    code: 'M1_BULK',
    shortCode: 'M1',
    label: 'Bulk Load',
    fullLabel: 'M1 • Bulk Load',
    description: 'Initial snapshot data migration without continuous replication.',
    supportsCutover: false,
    isValidationAssurance: false
  },
  M2_BULK_CDC: {
    code: 'M2_BULK_CDC',
    shortCode: 'M2',
    label: 'Bulk + CDC',
    fullLabel: 'M2 • Bulk + CDC',
    description: 'Initial bulk snapshot followed by low-latency CDC replication and cutover.',
    supportsCutover: true,
    isValidationAssurance: false
  },
  M3_CDC: {
    code: 'M3_CDC',
    shortCode: 'M3',
    label: 'CDC Only',
    fullLabel: 'M3 • CDC Only',
    description: 'Continuous change data capture streaming from active transaction logs.',
    supportsCutover: true,
    isValidationAssurance: false
  },
  M4_INCREMENTAL: {
    code: 'M4_INCREMENTAL',
    shortCode: 'M4',
    label: 'Incremental',
    fullLabel: 'M4 • Incremental',
    description: 'Timestamp or watermark-based periodic batch delta replication.',
    supportsCutover: true,
    isValidationAssurance: false
  },
  M5_STATE_SYNC: {
    code: 'M5_STATE_SYNC',
    shortCode: 'M5',
    label: 'State Sync',
    fullLabel: 'M5 • State Sync',
    description: 'State-based reconciliation and multi-directional synchronization.',
    supportsCutover: true,
    isValidationAssurance: false
  },
  M6_SCHEMA_ONLY: {
    code: 'M6_SCHEMA_ONLY',
    shortCode: 'M6',
    label: 'Schema Only',
    fullLabel: 'M6 • Schema Only',
    description: 'DDL structural extraction, conversion, and target object creation.',
    supportsCutover: false,
    isValidationAssurance: false
  },
  M7_DATA_ONLY: {
    code: 'M7_DATA_ONLY',
    shortCode: 'M7',
    label: 'Data Only',
    fullLabel: 'M7 • Data Only',
    description: 'Data payload migration into pre-existing target schema objects.',
    supportsCutover: false,
    isValidationAssurance: false
  },
  M8_VALIDATION_ONLY: {
    code: 'M8_VALIDATION_ONLY',
    shortCode: 'M8',
    label: 'Validation Only',
    fullLabel: 'M8 • Validation Only',
    description: 'Independent Data Synchronization Assurance & forensic discrepancy audit.',
    supportsCutover: false,
    isValidationAssurance: true
  }
};

export type HistoryOutcome =
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLED'
  | 'STOPPED'
  | 'RUNNING'
  | 'PAUSED'
  | 'ABORTED'
  | 'INTERRUPTED';

export type ValidationReconciliationState =
  | 'PASSED'
  | 'FAILED'
  | 'MISMATCHES_DETECTED'
  | 'RECONCILED'
  | 'SKIPPED'
  | 'NOT_CONFIGURED'
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'UNAVAILABLE';

export type EvidenceAvailability =
  | 'AVAILABLE'
  | 'SEALED'
  | 'PENDING_EXPORT'
  | 'NOT_GENERATED'
  | 'UNAVAILABLE'
  | 'CORRUPTED'
  | 'PURGED';

export type EvidenceIntegrity =
  | 'SHA256_VERIFIED'
  | 'UNVERIFIED'
  | 'HASH_MISMATCH'
  | 'NOT_APPLICABLE'
  | 'UNKNOWN';

export type CutoverStatus =
  | 'COMPLETED'
  | 'ABORTED'
  | 'ROLLED_BACK'
  | 'NOT_APPLICABLE'
  | 'SCHEDULED'
  | 'MANUAL_PENDING'
  | 'IN_PROGRESS'
  | 'UNKNOWN';

export type RecoveryStatus =
  | 'NONE'
  | 'RESTORED'
  | 'POINT_IN_TIME_RECOVERED'
  | 'FAILED'
  | 'NOT_TRIGGERED'
  | 'NOT_APPLICABLE';

export interface HistoryContinuityContext {
  cutoverStatus: CutoverStatus;
  recoveryStatus: RecoveryStatus;
  cdcLagSeconds: number | null;
  cutoverDowntimeSeconds: number | null;
  cutoverCompletedAt: string | null;
  rollbackTriggeredAt: string | null;
  rollbackReason: string | null;
}

export interface MigrationHistoryItem {
  id: string;                          // Unique ledger item ID e.g. "hist-001"
  migrationId: string;                 // Parent migration ID e.g. "mig-core-ledger-01"
  migrationName: string;               // Display name e.g. "Core Financial Transaction Ledger"
  executionId: string;                 // Run execution ID e.g. "exec-20260908-0192"
  projectId: string;                   // Project UUID / identifier
  projectName: string;                 // Project display name
  initiativeName?: string;             // Optional parent initiative name
  sourceProvider: string;              // e.g. "Oracle Database 19c Enterprise"
  sourceProviderCode: string;          // e.g. "oracle"
  targetProvider: string;              // e.g. "PostgreSQL 16.2 Cloud Native"
  targetProviderCode: string;          // e.g. "postgres"
  mode: HistoryMode;                   // M1 through M8
  outcome: HistoryOutcome;             // SUCCEEDED, FAILED, etc.
  errorMessage: string | null;         // Error detail if failed
  validationState: ValidationReconciliationState;
  validationDiscrepancyCount: number;  // Number of mismatches (0 if passed/none)
  evidenceAvailability: EvidenceAvailability;
  evidenceIntegrity: EvidenceIntegrity;
  evidenceDigest: string | null;       // SHA-256 digest string e.g. "sha256:4f8a..."
  evidenceSizeBytes: number | null;
  continuity: HistoryContinuityContext;
  operator: string;                    // Operator name / role
  startedAt: string;                   // ISO 8601 string
  completedAt: string | null;          // ISO 8601 string (null if running)
  durationString: string;              // Formatted duration e.g. "1h 42m 18s"
  rowsProcessed: number;               // Total rows transferred or audited
  throughputFormatted: string;         // e.g. "45,200 rows/s" or "32.4 MB/s"
}

export type HistoryAvailabilityState =
  | 'READY'
  | 'LOADING'
  | 'EMPTY'
  | 'UNAVAILABLE'
  | 'ERROR'
  | 'UNAUTHORIZED';

export type HistorySortOption =
  | 'completed_desc'
  | 'completed_asc'
  | 'name_asc'
  | 'name_desc'
  | 'duration_desc'
  | 'discrepancies_desc'
  | 'rows_desc';

export interface HistoryFilterState {
  searchQuery: string;
  project: string | 'ALL';
  mode: HistoryMode | 'ALL';
  outcome: HistoryOutcome | 'ALL';
  validationState: ValidationReconciliationState | 'ALL';
  evidence: string | 'ALL';
  continuity: string | 'ALL';
  sortBy: HistorySortOption;
}
