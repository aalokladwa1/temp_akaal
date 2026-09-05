/**
 * AKAAL Enterprise Migration Platform
 * Step 7: Dynamic Migration Plan (Models & Contracts)
 *
 * Governing Definition:
 * Steps 1-6 tell AKAAL what the operator wants.
 * Step 7 shows the operator what AKAAL will actually do.
 */

export type CanonicalPlanMode =
  | 'M1_BULK'
  | 'M2_BULK_CDC'
  | 'M3_CDC'
  | 'M4_INCREMENTAL'
  | 'M5_STATE_SYNC'
  | 'M6_SCHEMA_ONLY'
  | 'M7_DATA_ONLY';

export type PlanNodeType = 'EXECUTION_STAGE' | 'APPROVAL_BARRIER';

export type PlanCategory = 'INGESTION' | 'TRANSFORMATION' | 'VALIDATION' | 'GOVERNANCE' | 'SYSTEM';

export type PlanStageType =
  | 'PRE_FLIGHT'
  | 'SCHEMA_DDL'
  | 'DATA_PREPARATION'
  | 'BULK_EXTRACT'
  | 'BULK_LOAD'
  | 'CDC_CAPTURE'
  | 'CDC_APPLY'
  | 'STATE_COMPARE'
  | 'INDEX_REBUILD'
  | 'POST_VALIDATION'
  | 'CUTOVER'
  | 'ROLLBACK_GUARD'
  | 'APPROVAL_BARRIER'
  | 'CUSTOM_SQL';

export type ProvenanceType = 'EXACT' | 'ESTIMATED' | 'UNAVAILABLE';

export type ApprovalBarrierPolicy =
  | 'FOUR_EYES'
  | 'SOLE_OWNER'
  | 'CAB_COMMITTEE'
  | 'DUAL_DBA_SEC'
  | 'CUSTOM';

export type ApprovalRejectionAction = 'HALT_MIGRATION' | 'FAIL_FAST' | 'ROLLBACK_TO_CHECKPOINT';

export type ApprovalTimeoutAction = 'ALERT_AND_HOLD' | 'AUTO_REJECT' | 'ROLLBACK_STAGE';

export type PlanReviewCategory = 'MUST_RESOLVE' | 'REVIEW_REQUIRED' | 'ADVISORY';

export type PlanSeverity = 'BLOCKER' | 'WARNING' | 'INFO';

export interface PlanWorkObject {
  id: string;
  name: string;
  schema: string;
  type: 'TABLE' | 'PARTITION' | 'VIEW' | 'PROCEDURE' | 'SEQUENCE' | 'INDEX';
  strategy: string;
  estimatedRows: number;
  rowsProvenance: ProvenanceType;
  estimatedSizeBytes: number;
  sizeProvenance: ProvenanceType;
  partitionCount: number;
  status: string;
}

export interface StageResolvedConfig {
  workerAllocation: number;
  batchSizeMb: number;
  recoveryStrategy: string;
  checkpointIntervalSec: number;
  retryPolicy: string;
  timeoutMinutes: number;
  customSqlBefore?: string;
  customSqlAfter?: string;
  upstreamStepOwner: number; // e.g. Step 6
}

export interface ApprovalBarrierConfig {
  id: string;
  gateName: string;
  description: string;
  protectedOperation: string;
  signerPolicy: ApprovalBarrierPolicy;
  requiredSignatures: number;
  approverRoles: string[];
  separationOfDuties: boolean; // SoD: creator cannot sign
  cdcMaxLagMs?: number;
  requireDlqEmpty: boolean;
  requireCheckpointClean: boolean;
  requireValidationPass: boolean;
  requireTargetTablesEmpty: boolean;
  rejectionAction: ApprovalRejectionAction;
  timeoutMinutes: number;
  timeoutAction: ApprovalTimeoutAction;
  planBindingHash: string;
  isMandatory: boolean;
  policyLocked: boolean;
  lockReason?: string;
  afterStageId: string;
  beforeStageId: string;
}

export interface PlanDagNode {
  id: string;
  order: number;
  label: string;
  subtitle: string;
  stageType: PlanStageType;
  nodeType: PlanNodeType;
  category: PlanCategory;
  description: string;
  purpose: string;
  isContinuous: boolean;
  continuousLabel?: string;
  estimatedDuration: string;
  workerAllocation?: number;
  batchSizeMb?: number;
  status: 'READY' | 'CONFIGURED' | 'PENDING' | 'LOCKED';
  isMandatoryBarrier?: boolean;
  policyLocked?: boolean;
  lockReason?: string;
  incomingDependencyIds: string[];
  outgoingDependencyIds: string[];
  workObjects?: PlanWorkObject[];
  resolvedConfig?: StageResolvedConfig;
  barrierConfig?: ApprovalBarrierConfig;
  hasIssues?: boolean;
  issueIds?: string[];
  // Topological level/branching for deterministic layout
  layer?: number;
  branchIndex?: number;
  totalBranches?: number;
}

export interface PlanDagEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  isApprovalBarrierEligible: boolean;
  hasApprovalBarrier: boolean;
  barrierId?: string;
}

export interface PlanReviewIssue {
  id: string;
  category: PlanReviewCategory;
  severity: PlanSeverity;
  title: string;
  impact: string;
  affectedScope: string;
  upstreamStep?: number;
  upstreamStepLabel?: string;
  stageId?: string;
  canAcknowledge?: boolean;
  isAcknowledged?: boolean;
  acknowledgementReason?: string;
}

export interface PlanSummaryData {
  migration: {
    sourceEngine: string;
    sourceEndpoint: string;
    targetEngine: string;
    targetEndpoint: string;
    mode: CanonicalPlanMode;
    modeLabel: string;
    environment: string;
  };
  scope: {
    totalObjects: number;
    totalPartitions: number;
    filterRuleCount: number;
    mappingRuleCount: number;
    dataControlCount: number;
    totalEstimatedBytes: number;
    totalEstimatedRows: number;
  };
  execution: {
    profile: string;
    workerConcurrency: number;
    chunkBufferMb: number;
    recoveryStrategy: string;
    cdcStreaming: string;
  };
  assurance: {
    validationMode: string;
    samplingRate: string;
    checksumPolicy: string;
    approvalGateCount: number;
  };
}

export interface TechnicalPlanDetails {
  planId: string;
  version: string;
  canonicalFingerprint: string;
  compilerScheme: string;
  targetEngineDescriptor: string;
  generatedTimestamp: string;
  redactedJsonDefinition: string;
}

export interface NewGateDraft {
  placementEdgeId: string;
  gateName: string;
  description: string;
  protectedOperation: string;
  signerPolicy: ApprovalBarrierPolicy;
  requiredSignatures: number;
  cdcMaxLagMs: number;
  requireDlqEmpty: boolean;
  requireCheckpointClean: boolean;
  requireValidationPass: boolean;
  requireTargetTablesEmpty: boolean;
  timeoutMinutes: number;
  timeoutAction: ApprovalTimeoutAction;
  rejectionAction: ApprovalRejectionAction;
}

export interface Step7PlanDescriptor {
  mode: CanonicalPlanMode;
  environment: string;
  sourceEngine: string;
  targetEngine: string;
  schemaVersion: string;
  modelSignature: string;
  fingerprint: string;
  nodes: PlanDagNode[];
  edges: PlanDagEdge[];
  summary: PlanSummaryData;
  issues: PlanReviewIssue[];
  technicalDetails: TechnicalPlanDetails;
}

