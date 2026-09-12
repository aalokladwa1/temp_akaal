/**
 * AKAAL Migration History Workspace Domain & Presentation Models
 * 
 * Defines canonical data contracts for all 10 destinations of the Migration History Workspace:
 * 1. Overview
 * 2. Timeline
 * 3. Execution
 * 4. Plan & Configuration
 * 5. Approvals & Governance
 * 6. Validation & Reconciliation
 * 7. Cutover & Continuity
 * 8. Recovery
 * 9. Evidence
 * 10. Audit Trail
 */

import {
  HistoryMode,
  HistoryOutcome,
  ValidationReconciliationState,
  EvidenceAvailability,
  EvidenceIntegrity,
  CutoverStatus,
  RecoveryStatus,
  HistoryModeDescriptor,
  HISTORY_MODE_DESCRIPTORS
} from '../history-home.models';

export type HistoryWorkspaceTab =
  | 'overview'
  | 'timeline'
  | 'execution'
  | 'plan'
  | 'governance'
  | 'validation'
  | 'cutover'
  | 'recovery'
  | 'evidence'
  | 'audit';

export interface WorkspaceTabDescriptor {
  id: HistoryWorkspaceTab;
  label: string;
  badge?: string;
  icon?: string;
}

export const HISTORY_WORKSPACE_TABS: WorkspaceTabDescriptor[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'execution', label: 'Execution' },
  { id: 'plan', label: 'Plan & Configuration' },
  { id: 'governance', label: 'Approvals & Governance' },
  { id: 'validation', label: 'Validation & Reconciliation' },
  { id: 'cutover', label: 'Cutover & Continuity' },
  { id: 'recovery', label: 'Recovery' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'audit', label: 'Audit Trail' }
];

// --- 1. TIMELINE MODELS ---
export type TimelineCategory =
  | 'LIFECYCLE'
  | 'PLANNING'
  | 'GOVERNANCE'
  | 'EXECUTION'
  | 'VALIDATION'
  | 'CONTINUITY'
  | 'RECOVERY'
  | 'SYSTEM'
  | 'OPERATOR';

export type TimelineSeverity = 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';

export interface TimelineEventItem {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  category: TimelineCategory;
  severity: TimelineSeverity;
  actor: string;
  correlationId?: string;
  metadata?: Record<string, string | number | boolean>;
}

// --- 2. EXECUTION & ATTEMPT MODELS ---
export interface ExecutionAttempt {
  attemptNumber: number;
  invocationId: string;
  state: 'SUCCEEDED' | 'FAILED' | 'RETRYING' | 'CANCELLED';
  startedAt: string;
  completedAt: string | null;
  duration: string;
  errorReason: string | null;
  checkpointResumeId: string | null;
  fenceEpoch: number;
}

export interface ExecutionNodeStage {
  id: string;
  name: string;
  stageType: 'EXTRACT' | 'TRANSFORM' | 'LOAD' | 'RECONCILE' | 'DDL_APPLY' | 'STREAM_CDC' | 'VALIDATE';
  status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'SKIPPED';
  startedAt: string;
  completedAt: string | null;
  duration: string;
  rowsIn: number;
  rowsOut: number;
  throughput: string;
  errorMessage?: string;
}

export interface ExecutionRunDetail {
  runId: string;
  executionId: string;
  runNumber: number;
  outcome: HistoryOutcome;
  startedAt: string;
  completedAt: string | null;
  duration: string;
  totalRowsProcessed: number;
  totalBytesProcessed: string;
  avgThroughput: string;
  cdcBacklogSeconds?: number | null;
  cdcEventsProcessed?: number | null;
  watermarkProgression?: string | null;
  attempts: ExecutionAttempt[];
  stages: ExecutionNodeStage[];
  errorMessage: string | null;
}

// --- 3. PLAN & CONFIGURATION MODELS ---
export interface PlanRevision {
  revisionNumber: number;
  planId: string;
  fingerprint: string; // SHA-256 fingerprint
  createdAt: string;
  createdBy: string;
  changeSummary: string;
  isCurrentExecutionPlan: boolean;
}

export interface PlanConfigSection {
  title: string;
  description: string;
  entries: { label: string; value: string; isSensitive?: boolean; mono?: boolean }[];
}

export interface PlanDiffItem {
  fieldName: string;
  category: string;
  oldValue: string;
  newValue: string;
  impactLevel: 'CRITICAL' | 'MODERATE' | 'INFORMATIONAL';
}

// --- 4. APPROVALS & GOVERNANCE MODELS ---
export interface ApproverDecision {
  approverName: string;
  role: string;
  decision: 'APPROVED' | 'REJECTED' | 'PENDING' | 'EXPIRED';
  decidedAt: string | null;
  comment: string | null;
}

export interface GovernanceBarrierRecord {
  barrierId: string;
  protectedOperation: string;
  requestedAt: string;
  requesterName: string;
  makerCheckerSatisfied: boolean;
  quorumRequired: number;
  quorumSatisfied: number;
  status: 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'TIMED_OUT' | 'SUPERSEDED' | 'INVALIDATED';
  planFingerprintBinding: string;
  expiresAt: string | null;
  approvers: ApproverDecision[];
  decisionNotes: string | null;
}

// --- 5. VALIDATION & RECONCILIATION MODELS ---
export interface DiscrepancyItem {
  id: string;
  tableName: string;
  primaryKey: string;
  discrepancyType: 'MISSING_IN_TARGET' | 'VALUE_MISMATCH' | 'TYPE_CONVERSION_ERROR' | 'UNRESOLVED_FK';
  sourceValue: string;
  targetValue: string;
  progression: 'DETECTED' | 'LOCALIZED' | 'REVIEWED' | 'REPAIRED' | 'REVALIDATED' | 'RESOLVED';
  reconciledAt: string | null;
  repairScriptSnippet: string | null;
}

export interface ValidationRunRecord {
  validationRunId: string;
  phase: 'PRE_MIGRATION' | 'IN_FLIGHT' | 'POST_MIGRATION' | 'REVALIDATION';
  startedAt: string;
  completedAt: string;
  duration: string;
  verdict: ValidationReconciliationState;
  rowCountSource: number;
  rowCountTarget: number;
  rowCountDelta: number;
  merkleTreeRootMatch: boolean;
  discrepancyCount: number;
  discrepancies: DiscrepancyItem[];
}

// --- 6. CUTOVER & CONTINUITY MODELS ---
export interface CutoverEventChronology {
  stepName: string;
  status: 'COMPLETED' | 'SKIPPED' | 'FAILED' | 'IN_PROGRESS' | 'NOT_APPLICABLE';
  timestamp: string | null;
  duration: string | null;
  details: string;
}

export interface CutoverContinuityRecord {
  isApplicableToMode: boolean;
  cutoverStatus: CutoverStatus;
  recoveryStatus: RecoveryStatus;
  cutoverPlannedAt: string | null;
  cutoverExecutedAt: string | null;
  downtimeSeconds: number | null;
  cdcFinalLagSeconds: number | null;
  finalSyncCatchupSeconds: number | null;
  postCutoverVerificationPassed: boolean;
  failbackReady: boolean;
  failbackInvoked: boolean;
  failbackReason: string | null;
  chronology: CutoverEventChronology[];
}

// --- 7. RECOVERY MODELS ---
export interface CheckpointRecord {
  checkpointId: string;
  generation: number;
  createdAt: string;
  associatedStage: string;
  isSelectedForResume: boolean;
  isSuperseded: boolean;
  fenceEpoch: number;
  committedRowsWatermark: number;
}

export interface RecoveryExecutionRecord {
  hasRecoveryOccurred: boolean;
  recoveryTriggerReason: string | null;
  recoveryTriggeredAt: string | null;
  recoveredAt: string | null;
  checkpointResumedFrom: CheckpointRecord | null;
  fenceEpoch: number;
  dataSafetyAttestation: string;
  checkpoints: CheckpointRecord[];
  residualExceptions: string[];
}

// --- 8. EVIDENCE & SEAL MODELS ---
export interface EvidenceFactItem {
  id: string;
  category: 'PLAN' | 'GOVERNANCE' | 'EXECUTION' | 'VALIDATION' | 'CUTOVER' | 'RECOVERY';
  name: string;
  digest: string;
  recordedAt: string;
  verified: boolean;
}

export interface EvidenceManifestItem {
  manifestId: string;
  executionId: string;
  generatedAt: string;
  completeness: 'COMPLETE' | 'PARTIAL' | 'INCOMPLETE';
  artifactCount: number;
  totalSizeBytes: number;
  digestVerification: 'SHA256_VERIFIED' | 'UNVERIFIED' | 'HASH_MISMATCH' | 'UNAVAILABLE';
  rootDigestSha256: string;
}

export interface ExecutionIdentitySealRecord {
  sealVersion: string;
  fingerprintSha256: string;
  fields: { name: string; value: string }[];
}

export interface EvidenceRecord {
  availability: EvidenceAvailability;
  integrity: EvidenceIntegrity;
  completeness: 'COMPLETE' | 'PARTIAL' | 'INCOMPLETE';
  manifests: EvidenceManifestItem[];
  artifacts: EvidenceFactItem[];
  identitySeal: ExecutionIdentitySealRecord;
  lastIntegrityCheckAt: string | null;
  integrityVerificationNotes: string;
}

// --- 9. AUDIT TRAIL MODELS ---
export interface AuditTrailEvent {
  id: string;
  timestamp: string;
  actorPrincipal: string;
  actorRole: string;
  action: string;
  resourceTarget: string;
  outcome: 'SUCCESS' | 'DENIED' | 'FAILED' | 'CHALLENGED';
  correlationExecutionId: string;
  beforeSnapshotJson?: string | null;
  afterSnapshotJson?: string | null;
  evidenceRefId?: string | null;
  hashChainLinkSha256: string;
}

// --- COMPLETE WORKSPACE RECORD ---
export interface MigrationHistoryWorkspaceRecord {
  id: string;                          // e.g. "mig-fin-core-01"
  migrationId: string;
  migrationName: string;
  executionId: string;
  projectId: string;
  projectName: string;
  initiativeName?: string;
  sourceProvider: string;
  sourceProviderCode: string;
  targetProvider: string;
  targetProviderCode: string;
  mode: HistoryMode;
  outcome: HistoryOutcome;
  lifecycleState: string;
  startedAt: string;
  completedAt: string | null;
  durationString: string;
  totalRowsProcessed: number;
  throughputFormatted: string;
  errorMessage: string | null;
  operator: string;
  
  // 10 Detailed Destination Projections:
  timeline: TimelineEventItem[];
  executionRuns: ExecutionRunDetail[];
  planAndConfig: {
    currentPlanId: string;
    planFingerprint: string;
    revisions: PlanRevision[];
    sections: PlanConfigSection[];
    semanticDiffs: PlanDiffItem[];
  };
  governance: GovernanceBarrierRecord[];
  validationRuns: ValidationRunRecord[];
  cutover: CutoverContinuityRecord;
  recovery: RecoveryExecutionRecord;
  evidence: EvidenceRecord;
  auditTrail: AuditTrailEvent[];
  
  materialExceptions: string[];
}
